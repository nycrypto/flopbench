"""Bounded streaming adapters for Ollama and OpenAI-compatible runtimes."""

from __future__ import annotations

import http.client
import json
from threading import Event
from time import perf_counter
from typing import Any

from flopbench.benchmark.adapters import (
    AdapterCancelledError,
    AdapterError,
    AdapterPartialError,
    AdapterRequest,
    AdapterSample,
    AdapterTimeoutError,
)
from flopbench.benchmark.endpoint import SafeEndpoint
from flopbench.benchmark.models import BenchmarkAdapterIdentity, BenchmarkModelIdentity

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024


class _HttpAdapter:
    def __init__(self, endpoint: SafeEndpoint) -> None:
        self.endpoint = endpoint
        self._active: http.client.HTTPConnection | None = None

    def _connection(self, timeout: float) -> http.client.HTTPConnection:
        connection_type = (
            http.client.HTTPSConnection
            if self.endpoint.scheme == "https"
            else http.client.HTTPConnection
        )
        connection = connection_type(self.endpoint.host, self.endpoint.port, timeout=timeout)
        self._active = connection
        return connection

    def _path(self, route: str) -> str:
        return f"{self.endpoint.base_path}{route}" or "/"

    def _request(
        self,
        method: str,
        route: str,
        *,
        timeout: float,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[http.client.HTTPConnection, http.client.HTTPResponse]:
        connection = self._connection(timeout)
        try:
            connection.request(method, self._path(route), body=body, headers=headers or {})
            response = connection.getresponse()
        except TimeoutError as exc:
            connection.close()
            self._active = None
            raise AdapterTimeoutError("Runtime request timed out") from exc
        except OSError as exc:
            connection.close()
            self._active = None
            raise AdapterError("Runtime connection failed") from exc
        if 300 <= response.status < 400:
            connection.close()
            self._active = None
            raise AdapterError("Runtime redirect was rejected")
        if response.status < 200 or response.status >= 300:
            connection.close()
            self._active = None
            raise AdapterError(f"Runtime returned HTTP {response.status}")
        return connection, response

    def _json(self, route: str, *, timeout: float) -> dict[str, Any]:
        connection, response = self._request("GET", route, timeout=timeout)
        try:
            content_length = response.getheader("Content-Length")
            if content_length is not None and int(content_length) > MAX_RESPONSE_BYTES:
                raise AdapterError("Runtime response exceeds the size limit")
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise AdapterError("Runtime response exceeds the size limit")
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise AdapterError("Runtime returned malformed JSON")
            return payload
        except (ValueError, UnicodeDecodeError) as exc:
            raise AdapterError("Runtime returned malformed JSON") from exc
        finally:
            connection.close()
            self._active = None

    @staticmethod
    def _reject_oversized_header(response: http.client.HTTPResponse) -> None:
        content_length = response.getheader("Content-Length")
        if content_length is not None:
            try:
                declared_length = int(content_length)
            except ValueError as exc:
                raise AdapterError("Runtime Content-Length is invalid") from exc
            if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
                raise AdapterError("Runtime response exceeds the size limit")

    def close(self) -> None:
        if self._active is not None:
            self._active.close()
            self._active = None


class OllamaAdapter(_HttpAdapter):
    """Ollama `/api/generate` NDJSON streaming adapter."""

    def __init__(self, endpoint: SafeEndpoint) -> None:
        super().__init__(endpoint)
        self.identity = BenchmarkAdapterIdentity(
            name="ollama", runtime_version="unknown", endpoint_scope=endpoint.scope
        )

    def run(self, request: AdapterRequest, cancel: Event) -> AdapterSample:
        body = json.dumps(
            {
                "model": self._model_name,
                "prompt": request.prompt,
                "stream": True,
                "options": {"seed": request.seed, "num_predict": request.max_tokens},
            },
            separators=(",", ":"),
        ).encode()
        connection, response = self._request(
            "POST",
            "/api/generate",
            timeout=request.timeout_seconds,
            body=body,
            headers={"Content-Type": "application/json"},
        )
        self._reject_oversized_header(response)
        started = perf_counter()
        first_token_at: float | None = None
        raw = bytearray()
        text_seen = False
        try:
            while True:
                if cancel.is_set():
                    raise AdapterCancelledError("Benchmark cancelled")
                line = response.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_LINE_BYTES or len(raw) + len(line) > MAX_RESPONSE_BYTES:
                    raise AdapterError("Runtime response exceeds the size limit")
                raw.extend(line)
                try:
                    chunk = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    if text_seen:
                        raise AdapterPartialError(
                            self._partial_sample(started, first_token_at, bytes(raw))
                        ) from exc
                    raise AdapterError("Ollama stream is malformed") from exc
                if not isinstance(chunk, dict):
                    raise AdapterError("Ollama stream is malformed")
                response_text = chunk.get("response")
                if isinstance(response_text, str) and response_text:
                    text_seen = True
                    if first_token_at is None:
                        first_token_at = perf_counter()
                if chunk.get("done") is True:
                    finished = perf_counter()
                    tokens = chunk.get("eval_count")
                    duration_ns = chunk.get("eval_duration")
                    if (
                        first_token_at is None
                        or not isinstance(tokens, int)
                        or isinstance(tokens, bool)
                        or tokens < 0
                        or not isinstance(duration_ns, int)
                        or isinstance(duration_ns, bool)
                        or duration_ns <= 0
                    ):
                        raise AdapterError("Ollama final metrics are invalid")
                    return AdapterSample(
                        ttft_seconds=first_token_at - started,
                        latency_seconds=finished - started,
                        generated_tokens=tokens,
                        tokens_per_second=tokens / (duration_ns / 1_000_000_000),
                        raw_response=bytes(raw),
                    )
            if text_seen:
                raise AdapterPartialError(self._partial_sample(started, first_token_at, bytes(raw)))
            raise AdapterError("Ollama stream ended without output")
        except TimeoutError as exc:
            if text_seen:
                raise AdapterPartialError(
                    self._partial_sample(started, first_token_at, bytes(raw))
                ) from exc
            raise AdapterTimeoutError("Runtime request timed out") from exc
        finally:
            connection.close()
            self._active = None

    def _partial_sample(
        self, started: float, first_token_at: float | None, raw: bytes
    ) -> AdapterSample:
        finished = perf_counter()
        ttft = 0.0 if first_token_at is None else first_token_at - started
        return AdapterSample(
            ttft_seconds=ttft,
            latency_seconds=finished - started,
            generated_tokens=0,
            tokens_per_second=0.0,
            raw_response=raw,
        )

    def model_identity(self, model: str) -> BenchmarkModelIdentity:
        identity = self._load_model_identity(model)
        self._model_name = model
        return identity

    def _load_model_identity(self, model: str) -> BenchmarkModelIdentity:
        version = self._json("/api/version", timeout=5.0).get("version")
        tags = self._json("/api/tags", timeout=10.0).get("models")
        if not isinstance(version, str) or not version:
            raise AdapterError("Ollama version response is invalid")
        if not isinstance(tags, list):
            raise AdapterError("Ollama model list is invalid")
        digest: str | None = None
        for item in tags:
            if isinstance(item, dict) and item.get("name") == model:
                candidate = item.get("digest")
                if isinstance(candidate, str):
                    digest = candidate.removeprefix("sha256:")
                    break
        if (
            digest is None
            or len(digest) != 64
            or any(ch not in "0123456789abcdef" for ch in digest)
        ):
            raise AdapterError("Requested Ollama model digest was not found")
        self.identity = BenchmarkAdapterIdentity(
            name="ollama", runtime_version=version, endpoint_scope=self.endpoint.scope
        )
        return BenchmarkModelIdentity(name=model, digest=digest)


class OpenAICompatibleAdapter(_HttpAdapter):
    """Generic streaming `/chat/completions` adapter with required model digest."""

    def __init__(
        self,
        endpoint: SafeEndpoint,
        *,
        model_digest: str,
        runtime_version: str = "unknown",
        api_key: str | None = None,
    ) -> None:
        super().__init__(endpoint)
        self._model_digest = model_digest
        self._model_name = ""
        self._api_key = api_key
        self.identity = BenchmarkAdapterIdentity(
            name="openai-compatible",
            runtime_version=runtime_version,
            endpoint_scope=endpoint.scope,
        )

    def model_identity(self, model: str) -> BenchmarkModelIdentity:
        identity = BenchmarkModelIdentity(name=model, digest=self._model_digest)
        self._model_name = model
        return identity

    def run(self, request: AdapterRequest, cancel: Event) -> AdapterSample:
        body = json.dumps(
            {
                "model": self._model_name,
                "messages": [{"role": "user", "content": request.prompt}],
                "max_tokens": request.max_tokens,
                "seed": request.seed,
                "stream": True,
                "stream_options": {"include_usage": True},
            },
            separators=(",", ":"),
        ).encode()
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        connection, response = self._request(
            "POST",
            "/chat/completions",
            timeout=request.timeout_seconds,
            body=body,
            headers=headers,
        )
        self._reject_oversized_header(response)
        started = perf_counter()
        first_token_at: float | None = None
        completion_tokens: int | None = None
        raw = bytearray()
        content_seen = False
        try:
            while True:
                if cancel.is_set():
                    raise AdapterCancelledError("Benchmark cancelled")
                line = response.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                if len(line) > MAX_LINE_BYTES or len(raw) + len(line) > MAX_RESPONSE_BYTES:
                    raise AdapterError("Runtime response exceeds the size limit")
                raw.extend(line)
                stripped = line.strip()
                if not stripped or not stripped.startswith(b"data:"):
                    continue
                data = stripped[5:].strip()
                if data == b"[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    if content_seen:
                        raise AdapterPartialError(
                            self._partial_sample(
                                started, first_token_at, completion_tokens, bytes(raw)
                            )
                        ) from exc
                    raise AdapterError("OpenAI-compatible stream is malformed") from exc
                if not isinstance(chunk, dict):
                    raise AdapterError("OpenAI-compatible stream is malformed")
                choices = chunk.get("choices")
                if isinstance(choices, list):
                    for choice in choices:
                        if not isinstance(choice, dict):
                            continue
                        delta = choice.get("delta")
                        if (
                            isinstance(delta, dict)
                            and isinstance(delta.get("content"), str)
                            and delta["content"]
                        ):
                            content_seen = True
                            if first_token_at is None:
                                first_token_at = perf_counter()
                usage = chunk.get("usage")
                if isinstance(usage, dict):
                    candidate = usage.get("completion_tokens")
                    if (
                        isinstance(candidate, int)
                        and not isinstance(candidate, bool)
                        and candidate >= 0
                    ):
                        completion_tokens = candidate
            finished = perf_counter()
            if not content_seen or first_token_at is None or completion_tokens is None:
                if content_seen:
                    raise AdapterPartialError(
                        self._partial_sample(started, first_token_at, completion_tokens, bytes(raw))
                    )
                raise AdapterError("OpenAI-compatible stream ended without measurable output")
            generation_seconds = max(finished - first_token_at, 1e-12)
            return AdapterSample(
                ttft_seconds=first_token_at - started,
                latency_seconds=finished - started,
                generated_tokens=completion_tokens,
                tokens_per_second=completion_tokens / generation_seconds,
                raw_response=bytes(raw),
            )
        except TimeoutError as exc:
            if content_seen:
                raise AdapterPartialError(
                    self._partial_sample(started, first_token_at, completion_tokens, bytes(raw))
                ) from exc
            raise AdapterTimeoutError("Runtime request timed out") from exc
        finally:
            connection.close()
            self._active = None

    def _partial_sample(
        self,
        started: float,
        first_token_at: float | None,
        completion_tokens: int | None,
        raw: bytes,
    ) -> AdapterSample:
        finished = perf_counter()
        tokens = completion_tokens or 0
        generation_seconds = max(finished - (first_token_at or finished), 1e-12)
        return AdapterSample(
            ttft_seconds=0.0 if first_token_at is None else first_token_at - started,
            latency_seconds=finished - started,
            generated_tokens=tokens,
            tokens_per_second=tokens / generation_seconds,
            raw_response=raw,
        )
