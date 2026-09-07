from __future__ import annotations

import errno
import json
import select
import socket
import ssl
import subprocess
from threading import Event, Timer
from time import perf_counter
from typing import Any, cast

import pytest

from flopbench.benchmark import transport
from flopbench.benchmark.adapters import AdapterCancelledError, AdapterTimeoutError

pytestmark = pytest.mark.stage5


def _ok() -> None:
    pass


def test_deadline_and_cancellation_are_distinct() -> None:
    cancel = Event()
    transport.check_deadline(perf_counter(), 10, cancel)
    with pytest.raises(AdapterTimeoutError):
        transport.check_deadline(perf_counter() - 10, 1, cancel)
    cancel.set()
    with pytest.raises(AdapterCancelledError):
        transport.check_deadline(perf_counter(), 10, cancel)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1"])
def test_numeric_address_never_spawns_dns(host: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("literal IP must not spawn a resolver")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert transport._addresses(host, 80, _ok)[0][1] == (host, 80)


class _Resolver:
    def __init__(self, *, status: int = 0, running: bool = False) -> None:
        self.returncode = status
        self.running = running
        self.calls = 0
        self.killed = False

    def communicate(self, timeout: float | None = None) -> tuple[bytes, None]:
        self.calls += 1
        if self.calls == 1 and timeout is not None:
            raise subprocess.TimeoutExpired("resolver", timeout)
        return json.dumps([[2, 1, 6, "", ["127.0.0.1", 80]]]).encode(), None

    def poll(self) -> int | None:
        return None if self.running else self.returncode

    def kill(self) -> None:
        self.killed = True
        self.running = False


@pytest.mark.parametrize("status", [0, 1])
def test_dns_result_and_process_cleanup(status: int, monkeypatch: pytest.MonkeyPatch) -> None:
    process = _Resolver(status=status)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: process)
    if status:
        with pytest.raises(OSError, match="name resolution failed"):
            transport._addresses("runtime.example", 80, _ok)
    else:
        assert transport._addresses("runtime.example", 80, _ok) == [(2, ("127.0.0.1", 80))]
    assert process.calls == 3


def test_stuck_dns_is_killed_and_reaped_on_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    process = _Resolver(running=True)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: process)

    def cancel() -> None:
        raise AdapterCancelledError("cancel")

    with pytest.raises(AdapterCancelledError):
        transport._addresses("runtime.example", 80, cancel)
    assert process.killed
    assert process.calls == 1


class _Socket:
    def __init__(self, *, result: int = 0, error: int = 0) -> None:
        self.result = result
        self.error = error
        self.closed = False
        self.handshakes: list[BaseException | None] = []
        self.sends: list[BaseException | int] = []

    def setblocking(self, value: bool) -> None:
        assert value is False

    def connect_ex(self, address: Any) -> int:
        return self.result

    def getsockopt(self, *args: Any) -> int:
        return self.error

    def close(self) -> None:
        self.closed = True

    def do_handshake(self) -> None:
        value = self.handshakes.pop(0)
        if value is not None:
            raise value

    def send(self, data: Any) -> int:
        value = self.sends.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def _patch_socket(monkeypatch: pytest.MonkeyPatch, sock: _Socket) -> None:
    monkeypatch.setattr(socket, "socket", lambda *a: sock)
    monkeypatch.setattr(select, "select", lambda r, w, x, t: (r, w, x))


@pytest.mark.parametrize("result", [0, errno.EINPROGRESS, errno.ECONNREFUSED])
def test_tcp_immediate_pending_and_failed_connect(
    result: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    sock = _Socket(result=result)
    _patch_socket(monkeypatch, sock)
    if result == errno.ECONNREFUSED:
        with pytest.raises(OSError, match="connection failed"):
            transport.connect("127.0.0.1", 80, tls=False, check=_ok)
        assert sock.closed
    else:
        assert transport.connect("127.0.0.1", 80, tls=False, check=_ok) is cast(Any, sock)


def test_tcp_pending_socket_error_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _Socket(result=errno.EINPROGRESS, error=errno.ECONNREFUSED)
    _patch_socket(monkeypatch, sock)
    with pytest.raises(OSError, match="connection failed"):
        transport.connect("127.0.0.1", 80, tls=False, check=_ok)
    assert sock.closed


def test_tcp_pending_can_be_cancelled_before_writable(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _Socket(result=errno.EINPROGRESS)
    _patch_socket(monkeypatch, sock)
    monkeypatch.setattr(select, "select", lambda *a: ([], [], []))
    calls = 0

    def cancel() -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise AdapterCancelledError("cancel")

    with pytest.raises(AdapterCancelledError):
        transport.connect("127.0.0.1", 80, tls=False, check=cancel)
    assert sock.closed


@pytest.mark.parametrize("failure", [False, True])
def test_tls_handshake_waits_are_bounded_and_certificate_failure_closes_socket(
    failure: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sock = _Socket()
    sock.handshakes = [
        ssl.SSLWantReadError(),
        ssl.SSLWantWriteError(),
        ssl.SSLCertVerificationError() if failure else None,
    ]
    _patch_socket(monkeypatch, sock)
    monkeypatch.setattr(ssl, "SSLSocket", _Socket)

    class Context:
        def wrap_socket(self, value: Any, **kwargs: Any) -> _Socket:
            assert kwargs == {"server_hostname": "127.0.0.1", "do_handshake_on_connect": False}
            return sock

    monkeypatch.setattr(ssl, "create_default_context", Context)
    if failure:
        with pytest.raises(OSError, match="connection failed"):
            transport.connect("127.0.0.1", 443, tls=True, check=_ok)
        assert sock.closed
    else:
        assert transport.connect("127.0.0.1", 443, tls=True, check=_ok) is cast(Any, sock)


@pytest.mark.parametrize("lazy", [False, True])
def test_send_handles_partial_writes_and_tls_backpressure(
    lazy: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    sock = _Socket()
    sock.sends = [BlockingIOError(), ssl.SSLWantWriteError(), ssl.SSLWantReadError(), 1, 2]
    _patch_socket(monkeypatch, sock)
    monkeypatch.setattr(transport, "connect", lambda *a, **kw: sock)
    connection = transport.BoundedConnection("127.0.0.1", 80, tls=False, check=_ok)
    if not lazy:
        connection.sock = cast(socket.socket, sock)
    connection.send(b"abc")
    assert not sock.sends
    connection.close()
    assert sock.closed


def test_zero_byte_send_is_not_an_infinite_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = _Socket()
    sock.sends = [0]
    monkeypatch.setattr(transport, "connect", lambda *a, **kw: sock)
    connection = transport.BoundedConnection("127.0.0.1", 80, tls=False, check=_ok)
    with pytest.raises(OSError, match="connection closed"):
        connection.send(b"abc")
    connection.close()


def test_real_local_resolver_exits_without_leaking_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FLOPBENCH_OPENAI_API_KEY", "never-pass-to-resolver")
    monkeypatch.setattr(
        transport,
        "_RESOLVE",
        transport._RESOLVE + "; import os; assert 'FLOPBENCH_OPENAI_API_KEY' not in os.environ",
    )
    started = perf_counter()
    addresses = transport._addresses(
        "localhost",
        80,
        lambda: transport.check_deadline(started, 5, Event()),
    )
    assert addresses


@pytest.mark.parametrize("cancelled", [False, True])
def test_real_stalled_resolver_is_terminated_and_reaped(
    cancelled: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(transport, "_RESOLVE", "import time; time.sleep(10)")
    cancel = Event()
    timer = Timer(0.1, cancel.set)
    if cancelled:
        timer.start()
    processes: list[subprocess.Popen[bytes]] = []
    original = subprocess.Popen

    def capture(*args: Any, **kwargs: Any) -> subprocess.Popen[bytes]:
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(subprocess, "Popen", capture)
    started = perf_counter()

    def check() -> None:
        transport.check_deadline(started, 2 if cancelled else 0.15, cancel)

    try:
        with pytest.raises(AdapterCancelledError if cancelled else AdapterTimeoutError):
            transport._addresses("runtime.example", 80, check)
    finally:
        if cancelled:
            timer.cancel()
            timer.join()
    assert perf_counter() - started < 1.5
    assert len(processes) == 1
    assert processes[0].poll() is not None
