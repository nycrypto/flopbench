from __future__ import annotations

import http.client
import io
import json
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread, Timer
from threading import enumerate as enumerate_threads
from time import perf_counter, sleep
from typing import cast

import pytest

from flopbench.benchmark.adapters import (
    AdapterCancelledError,
    AdapterError,
    AdapterPartialError,
    AdapterRequest,
    AdapterTimeoutError,
)
from flopbench.benchmark.endpoint import validate_endpoint
from flopbench.benchmark.http_adapters import OllamaAdapter, OpenAICompatibleAdapter

DIGEST = "a" * 64


class _RuntimeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        del format, args

    def _write(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/bad/api/version":
            self._write(200, b"not-json", "application/json")
        elif self.path == "/huge/api/version":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(3 * 1024 * 1024))
            self.end_headers()
        elif self.path == "/status/api/version":
            self._write(503, b"{}", "application/json")
        elif self.path == "/api/version":
            self._write(200, b'{"version":"0.12.0"}', "application/json")
        elif self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "fixture:latest", "digest": DIGEST}]}).encode()
            self._write(200, body, "application/json")
        else:
            self._write(404, b"{}", "application/json")

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.server.requests.append((self.path, self.rfile.read(length)))  # type: ignore[attr-defined]
        if self.path.startswith(("/delay/", "/trickle/", "/silent/", "/eof/", "/bad-length/")):
            ollama = self.path.endswith("/api/generate")
            content = (
                b'{"response":"hello","done":false}\n'
                if ollama
                else b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            )
            final = (
                b'{"done":true,"eval_count":2,"eval_duration":100000000}\n'
                if ollama
                else b'data: {"usage":{"completion_tokens":2}}\n\ndata: [DONE]\n\n'
            )
            try:
                if self.path.startswith("/delay/"):
                    sleep(0.2)
                    self._write(200, content + final, "text/plain")
                elif self.path.startswith("/eof/"):
                    self._write(
                        200, content + final.replace(b"data: [DONE]\n\n", b""), "text/plain"
                    )
                else:
                    self.send_response(200)
                    self.send_header("Connection", "close")
                    if self.path.startswith("/bad-length/"):
                        self.send_header("Content-Length", "invalid")
                    self.end_headers()
                    self.close_connection = True
                    if self.path.startswith("/silent/"):
                        sleep(0.8)
                    elif self.path.startswith("/trickle/"):
                        self.wfile.write(content)
                        self.wfile.flush()
                        # No newline: socket activity must not reset the total deadline.
                        for _ in range(20):
                            self.wfile.write(b" ")
                            self.wfile.flush()
                            sleep(0.05)
            except OSError:
                pass  # Expected when the client cancels or reaches its deadline.
            return
        if self.path == "/api/generate":
            body = (
                b'{"response":"hello","done":false}\n'
                b'{"response":"","done":true,"eval_count":2,"eval_duration":100000000}\n'
            )
            self._write(200, body, "application/x-ndjson")
        elif self.path == "/partial/api/generate":
            self._write(200, b'{"response":"hello","done":false}\n', "application/x-ndjson")
        elif self.path == "/malformed/api/generate":
            self._write(200, b"not-json\n", "application/x-ndjson")
        elif self.path == "/malformed-after/api/generate":
            body = b'{"response":"hello","done":false}\nnot-json\n'
            self._write(200, body, "application/x-ndjson")
        elif self.path == "/v1/chat/completions":
            body = (
                b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
                b'data: {"choices":[],"usage":{"completion_tokens":3}}\n\n'
                b"data: [DONE]\n\n"
            )
            self._write(200, body, "text/event-stream")
        elif self.path == "/redirect/chat/completions":
            self.send_response(307)
            self.send_header("Location", "/v1/chat/completions")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif self.path == "/oversized/chat/completions":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(3 * 1024 * 1024))
            self.end_headers()
        elif self.path == "/partial/chat/completions":
            body = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
            self._write(200, body, "text/event-stream")
        elif self.path == "/malformed/chat/completions":
            self._write(200, b"data: not-json\n\n", "text/event-stream")
        elif self.path == "/malformed-after/chat/completions":
            body = b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\ndata: not-json\n\n'
            self._write(200, body, "text/event-stream")
        else:
            self._write(404, b"{}", "application/json")


@contextmanager
def _runtime() -> Iterator[tuple[str, list[tuple[str, bytes]]]]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RuntimeHandler)
    server.requests = []  # type: ignore[attr-defined]
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", server.requests  # type: ignore[attr-defined]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _request() -> AdapterRequest:
    return AdapterRequest(prompt="hello", max_tokens=8, seed=7, timeout_seconds=2)


def test_ollama_adapter_records_runtime_model_digest_and_raw_metrics() -> None:
    with _runtime() as (url, requests):
        adapter = OllamaAdapter(validate_endpoint(url))
        identity = adapter.model_identity("fixture:latest")
        sample = adapter.run(_request(), Event())
        adapter.close()

    assert identity.digest == DIGEST
    assert adapter.identity.runtime_version == "0.12.0"
    assert sample.generated_tokens == 2
    assert sample.tokens_per_second == 20
    sent = json.loads(requests[0][1])
    assert sent["model"] == "fixture:latest"
    assert sent["options"] == {"num_predict": 8, "seed": 7}


def test_openai_compatible_stream_records_usage() -> None:
    with _runtime() as (url, _):
        adapter = OpenAICompatibleAdapter(
            validate_endpoint(f"{url}/v1"), model_digest=DIGEST, runtime_version="fixture"
        )
        identity = adapter.model_identity("fixture")
        sample = adapter.run(_request(), Event())
        adapter.close()

    assert identity.digest == DIGEST
    assert sample.generated_tokens == 3
    assert sample.ttft_seconds >= 0
    assert sample.latency_seconds >= sample.ttft_seconds


@pytest.mark.parametrize("path", ["redirect", "oversized"])
def test_redirect_and_oversized_stream_are_rejected(path: str) -> None:
    with _runtime() as (url, _):
        adapter = OpenAICompatibleAdapter(validate_endpoint(f"{url}/{path}"), model_digest=DIGEST)
        adapter.model_identity("fixture")
        with pytest.raises(AdapterError):
            adapter.run(_request(), Event())
        adapter.close()


@pytest.mark.parametrize("path", ["bad", "huge", "status"])
def test_ollama_metadata_failures_are_safe(path: str) -> None:
    with _runtime() as (url, _):
        adapter = OllamaAdapter(validate_endpoint(f"{url}/{path}"))
        with pytest.raises(AdapterError):
            adapter.model_identity("fixture:latest")
        adapter.close()


@pytest.mark.parametrize(
    ("path", "partial"),
    [
        ("partial", True),
        ("malformed", False),
        ("malformed-after", True),
    ],
)
def test_ollama_incomplete_and_malformed_streams_are_classified(path: str, partial: bool) -> None:
    from flopbench.benchmark.adapters import AdapterPartialError

    with _runtime() as (url, _):
        adapter = OllamaAdapter(validate_endpoint(f"{url}/{path}"))
        adapter._model_name = "fixture:latest"
        expected = AdapterPartialError if partial else AdapterError
        with pytest.raises(expected):
            adapter.run(_request(), Event())
        adapter.close()


@pytest.mark.parametrize(
    ("path", "partial"),
    [("partial", True), ("malformed", False), ("malformed-after", True)],
)
def test_openai_incomplete_and_malformed_streams_are_classified(path: str, partial: bool) -> None:
    from flopbench.benchmark.adapters import AdapterPartialError

    with _runtime() as (url, _):
        adapter = OpenAICompatibleAdapter(validate_endpoint(f"{url}/{path}"), model_digest=DIGEST)
        adapter.model_identity("fixture")
        expected = AdapterPartialError if partial else AdapterError
        with pytest.raises(expected):
            adapter.run(_request(), Event())
        adapter.close()


def test_cancelled_stream_closes_active_connection() -> None:
    from flopbench.benchmark.adapters import AdapterCancelledError

    with _runtime() as (url, _):
        adapter = OpenAICompatibleAdapter(validate_endpoint(f"{url}/v1"), model_digest=DIGEST)
        adapter.model_identity("fixture")
        cancelled = Event()
        cancelled.set()
        with pytest.raises(AdapterCancelledError):
            adapter.run(_request(), cancelled)
        assert adapter._active is None


def _adapter(url: str, kind: str) -> OllamaAdapter | OpenAICompatibleAdapter:
    if kind == "ollama":
        adapter = OllamaAdapter(validate_endpoint(url))
        adapter._model_name = "fixture:latest"
        return adapter
    return OpenAICompatibleAdapter(validate_endpoint(url), model_digest=DIGEST)


@pytest.mark.parametrize("kind", ["ollama", "openai"])
def test_ttft_includes_delayed_response_headers(kind: str) -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/delay", kind)
        sample = adapter.run(_request(), Event())
        assert sample.ttft_seconds >= 0.18
        assert sample.latency_seconds >= sample.ttft_seconds
        assert adapter._active is None


@pytest.mark.parametrize("kind", ["ollama", "openai"])
@pytest.mark.parametrize("path", ["delay", "silent", "trickle"])
def test_total_deadline_includes_headers_and_trickling_body(kind: str, path: str) -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/{path}", kind)
        started = perf_counter()
        with pytest.raises(AdapterTimeoutError) as caught:
            adapter.run(AdapterRequest("test", 8, 7, 0.12), Event())
        if path == "trickle":
            assert caught.value.sample is not None
            assert caught.value.sample.generated_tokens is None
        assert perf_counter() - started < 0.7
        assert adapter._active is None
        assert not any(t.name == "flopbench-http-deadline" for t in enumerate_threads())


@pytest.mark.parametrize("kind", ["ollama", "openai"])
@pytest.mark.parametrize("path", ["delay", "silent", "trickle"])
def test_cancellation_interrupts_blocking_io(kind: str, path: str) -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/{path}", kind)
        cancel = Event()
        timer = Timer(0.08, cancel.set)
        timer.start()
        started = perf_counter()
        try:
            with pytest.raises(AdapterCancelledError) as caught:
                adapter.run(_request(), cancel)
            if path == "trickle":
                assert caught.value.sample is not None
        finally:
            timer.cancel()
            timer.join()
        assert perf_counter() - started < 0.7
        assert adapter._active is None
        assert not any(t.name == "flopbench-http-deadline" for t in enumerate_threads())


@pytest.mark.parametrize("kind", ["ollama", "openai"])
def test_invalid_header_closes_connection_without_caller_cleanup(kind: str) -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/bad-length", kind)
        with pytest.raises(AdapterError, match="Content-Length"):
            adapter.run(_request(), Event())
        assert adapter._active is None


def test_openai_eof_with_usage_but_without_done_is_partial() -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/eof", "openai")
        with pytest.raises(AdapterPartialError) as caught:
            adapter.run(_request(), Event())
        assert caught.value.sample.generated_tokens == 2
        assert caught.value.sample.tokens_per_second is None


@pytest.mark.parametrize("kind", ["ollama", "openai"])
def test_unknown_partial_token_count_is_null_not_zero(kind: str) -> None:
    with _runtime() as (url, _):
        adapter = _adapter(f"{url}/partial", kind)
        with pytest.raises(AdapterPartialError) as caught:
            adapter.run(_request(), Event())
        assert caught.value.sample.generated_tokens is None
        assert caught.value.sample.tokens_per_second is None


@pytest.mark.parametrize("kind", ["ollama", "openai"])
def test_deeply_nested_runtime_json_is_a_controlled_adapter_error(kind: str) -> None:
    raw = b"[" * 5000 + b"0" + b"]" * 5000 + b"\n"
    if kind == "openai":
        raw = b"data: " + raw
    adapter = _adapter("http://127.0.0.1", kind)
    response = cast(http.client.HTTPResponse, io.BytesIO(raw))
    with pytest.raises(AdapterError, match="malformed"):
        adapter._consume(response, perf_counter(), Event())
