from __future__ import annotations

import http.client
import io
from threading import Event
from typing import cast

import pytest

from flopbench.benchmark.adapters import AdapterCancelledError, AdapterError
from flopbench.benchmark.response_limits import (
    MAX_LINE_BYTES,
    MAX_RESPONSE_BYTES,
    bounded_body,
    bounded_lines,
    reject_unsafe_response,
)


class _Response(io.BytesIO):
    def __init__(self, body: bytes = b"", *, status: int = 200, length: str | None = None) -> None:
        super().__init__(body)
        self.status = status
        self.length = length

    def getheader(self, key: str) -> str | None:
        return self.length


def _response(*args: object, **kwargs: object) -> http.client.HTTPResponse:
    return cast(http.client.HTTPResponse, _Response(*args, **kwargs))  # type: ignore[arg-type]


@pytest.mark.parametrize("status", [199, 300, 399, 400, 503])
def test_status_and_redirect_rejection(status: int) -> None:
    with pytest.raises(AdapterError):
        reject_unsafe_response(_response(status=status))


@pytest.mark.parametrize("length", ["invalid", "-1", str(MAX_RESPONSE_BYTES + 1)])
def test_invalid_or_oversized_declared_length(length: str) -> None:
    with pytest.raises(AdapterError):
        reject_unsafe_response(_response(length=length))


@pytest.mark.parametrize("length", [None, "0", str(MAX_RESPONSE_BYTES)])
def test_bounded_declared_length(length: str | None) -> None:
    reject_unsafe_response(_response(length=length))


def test_actual_body_limit_without_trusting_headers() -> None:
    assert bounded_body(_response(b"ok")) == b"ok"
    with pytest.raises(AdapterError):
        bounded_body(_response(b"x" * (MAX_RESPONSE_BYTES + 1)))


def test_line_and_aggregate_limit_and_cancellation() -> None:
    assert list(bounded_lines(_response(b"one\ntwo\n"), Event())) == [b"one\n", b"two\n"]
    with pytest.raises(AdapterError):
        list(bounded_lines(_response(b"x" * (MAX_LINE_BYTES + 1)), Event()))
    with pytest.raises(AdapterError):
        list(bounded_lines(_response((b"x" * (MAX_LINE_BYTES - 1) + b"\n") * 17), Event()))
    cancel = Event()
    cancel.set()
    with pytest.raises(AdapterCancelledError):
        list(bounded_lines(_response(b"secret"), cancel))
