"""Bounded streaming adapters for Ollama and OpenAI-compatible runtimes."""

from __future__ import annotations

import http.client
import io
import json
import socket
from collections.abc import Callable
from threading import Event
from time import perf_counter
from typing import Any

from flopbench.benchmark.adapters import (
    AdapterError,
    AdapterPartialError,
    AdapterRequest,
    AdapterSample,
    AdapterTimeoutError,
)
from flopbench.benchmark.endpoint import SafeEndpoint
from flopbench.benchmark.models import BenchmarkAdapterIdentity, BenchmarkModelIdentity
from flopbench.benchmark.response_limits import bounded_body, bounded_lines, reject_unsafe_response
from flopbench.benchmark.transport import BoundedConnection, check_deadline


class _InterruptibleReader(io.RawIOBase):
    """Keep HTTP parser buffers intact while polling a silent socket for cancellation."""

    def __init__(self, sock: socket.socket, check: Callable[[], None]) -> None:
        self._socket = sock
        self._check = check
        # Keep the descriptor alive if HTTPConnection detaches a close-delimited response.
        self._lease = sock.makefile("rb", buffering=0)

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Any) -> int:
        while True:
            self._check()
            try:
                return self._socket.recv_into(buffer)
            except TimeoutError:
                continue

    def close(self) -> None:
        self._lease.close()
        super().close()


class _ResponseSocket:
    def __init__(self, sock: socket.socket, check: Callable[[], None]) -> None:
        self.sock = sock
        self.check = check

    def makefile(self, mode: str) -> io.BufferedReader:
        return io.BufferedReader(_InterruptibleReader(self.sock, self.check))


class _HttpAdapter:
    def __init__(self, endpoint: SafeEndpoint) -> None:
        self.endpoint = endpoint
        self._active: http.client.HTTPConnection | None = None

    def _path(self, route: str) -> str:
        return f"{self.endpoint.base_path}{route}" or "/"

    def _exchange[T](
        self,
        method: str,
        route: str,
        *,
        timeout: float,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        cancel: Event | None = None,
        consume: Callable[[http.client.HTTPResponse, float], T],
    ) -> T:
        # Include connect, headers and the entire body in both the clock and deadline.
        started = perf_counter()
        cancellation = cancel if cancel is not None else Event()
        response: http.client.HTTPResponse | None = None

        def check(sample: AdapterSample | None = None) -> None:
            try:
                check_deadline(started, timeout, cancellation)
            except AdapterError as exc:
                exc.sample = sample
                raise

        connection = BoundedConnection(
            self.endpoint.host,
            self.endpoint.port,
            tls=self.endpoint.scheme == "https",
            check=check,
        )
        self._active = connection
        try:
            check()
            connection.connect()
            check()
            connection.request(method, self._path(route), body=body, headers=headers or {})
            assert connection.sock is not None
            connection.sock.settimeout(min(0.05, timeout))

            class InterruptibleResponse(http.client.HTTPResponse):
                def __init__(self, sock: socket.socket, **kwargs: Any) -> None:
                    super().__init__(_ResponseSocket(sock, check), **kwargs)  # type: ignore[arg-type]

            connection.response_class = InterruptibleResponse
            response = connection.getresponse()
            check()
            reject_unsafe_response(response)
            result = consume(response, started)
            check()
            return result
        except AdapterError as exc:
            check(exc.sample)
            raise
        except TimeoutError as exc:
            check()
            raise AdapterTimeoutError("Runtime request timed out") from exc
        except (OSError, http.client.HTTPException) as exc:
            check()
            raise AdapterError("Runtime connection failed") from exc
        finally:
            if response is not None:
                response.close()
            connection.close()
            self._active = None

    def _json(self, route: str, *, timeout: float) -> dict[str, Any]:
        def consume(response: http.client.HTTPResponse, started: float) -> dict[str, Any]:
            raw = bounded_body(response)
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeDecodeError, RecursionError) as exc:
                raise AdapterError("Runtime returned malformed JSON") from exc
            if not isinstance(payload, dict):
                raise AdapterError("Runtime returned malformed JSON")
            return payload

        return self._exchange("GET", route, timeout=timeout, consume=consume)

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
        return self._exchange(
            "POST",
            "/api/generate",
            timeout=request.timeout_seconds,
            body=body,
            headers={"Content-Type": "application/json"},
            cancel=cancel,
            consume=lambda response, started: self._consume(response, started, cancel),
        )

    def _consume(
        self, response: http.client.HTTPResponse, started: float, cancel: Event
    ) -> AdapterSample:
        first_token_at: float | None = None
        raw = bytearray()
        text_seen = False
        try:
            for line in bounded_lines(response, cancel):
                raw.extend(line)
                try:
                    chunk = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
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
        except AdapterError as exc:
            if text_seen and exc.sample is None:
                exc.sample = self._partial_sample(started, first_token_at, bytes(raw))
            raise
        except (OSError, http.client.HTTPException) as exc:
            if text_seen:
                raise AdapterPartialError(
                    self._partial_sample(started, first_token_at, bytes(raw))
                ) from exc
            raise

    def _partial_sample(
        self, started: float, first_token_at: float | None, raw: bytes
    ) -> AdapterSample:
        finished = perf_counter()
        ttft = 0.0 if first_token_at is None else first_token_at - started
        return AdapterSample(
            ttft_seconds=ttft,
            latency_seconds=finished - started,
            generated_tokens=None,
            tokens_per_second=None,
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
        return self._exchange(
            "POST",
            "/chat/completions",
            timeout=request.timeout_seconds,
            body=body,
            headers=headers,
            cancel=cancel,
            consume=lambda response, started: self._consume(response, started, cancel),
        )

    def _consume(
        self, response: http.client.HTTPResponse, started: float, cancel: Event
    ) -> AdapterSample:
        first_token_at: float | None = None
        completion_tokens: int | None = None
        raw = bytearray()
        content_seen = False
        done_seen = False
        try:
            for line in bounded_lines(response, cancel):
                raw.extend(line)
                stripped = line.strip()
                if not stripped or not stripped.startswith(b"data:"):
                    continue
                data = stripped[5:].strip()
                if data == b"[DONE]":
                    done_seen = True
                    break
                try:
                    chunk = json.loads(data)
                except (json.JSONDecodeError, UnicodeDecodeError, RecursionError) as exc:
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
            if not done_seen or first_token_at is None or completion_tokens is None:
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
        except AdapterError as exc:
            if content_seen and exc.sample is None:
                exc.sample = self._partial_sample(
                    started, first_token_at, completion_tokens, bytes(raw)
                )
            raise
        except (OSError, http.client.HTTPException) as exc:
            if content_seen:
                raise AdapterPartialError(
                    self._partial_sample(started, first_token_at, completion_tokens, bytes(raw))
                ) from exc
            raise

    def _partial_sample(
        self,
        started: float,
        first_token_at: float | None,
        completion_tokens: int | None,
        raw: bytes,
    ) -> AdapterSample:
        finished = perf_counter()
        return AdapterSample(
            ttft_seconds=0.0 if first_token_at is None else first_token_at - started,
            latency_seconds=finished - started,
            generated_tokens=completion_tokens,
            tokens_per_second=None,
            raw_response=raw,
        )
