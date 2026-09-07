"""Shared fail-closed HTTP response limits for every runtime adapter."""

from __future__ import annotations

import http.client
from collections.abc import Iterator
from threading import Event

from flopbench.benchmark.adapters import AdapterCancelledError, AdapterError

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024


def reject_unsafe_response(response: http.client.HTTPResponse) -> None:
    if 300 <= response.status < 400:
        raise AdapterError("Runtime redirect was rejected")
    if response.status < 200 or response.status >= 300:
        raise AdapterError(f"Runtime returned HTTP {response.status}")
    content_length = response.getheader("Content-Length")
    if content_length is not None:
        try:
            declared_length = int(content_length)
        except ValueError as exc:
            raise AdapterError("Runtime Content-Length is invalid") from exc
        if declared_length < 0 or declared_length > MAX_RESPONSE_BYTES:
            raise AdapterError("Runtime response exceeds the size limit")


def bounded_body(response: http.client.HTTPResponse) -> bytes:
    raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise AdapterError("Runtime response exceeds the size limit")
    return raw


def bounded_lines(response: http.client.HTTPResponse, cancel: Event) -> Iterator[bytes]:
    total = 0
    while True:
        if cancel.is_set():
            raise AdapterCancelledError("Benchmark cancelled")
        line = response.readline(MAX_LINE_BYTES + 1)
        if not line:
            return
        total += len(line)
        if len(line) > MAX_LINE_BYTES or total > MAX_RESPONSE_BYTES:
            raise AdapterError("Runtime response exceeds the size limit")
        yield line
