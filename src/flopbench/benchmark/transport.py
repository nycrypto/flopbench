"""Deadline-aware TCP/TLS transport, including cancellable DNS resolution."""

from __future__ import annotations

import errno
import http.client
import json
import os
import select
import socket
import ssl
import subprocess
import sys
from collections.abc import Callable
from ipaddress import ip_address
from threading import Event
from time import perf_counter
from typing import Any

from flopbench.benchmark.adapters import AdapterCancelledError, AdapterTimeoutError

_RESOLVE = (
    "import json,socket,sys; "
    "print(json.dumps(socket.getaddrinfo(sys.argv[1],int(sys.argv[2]),"
    "type=socket.SOCK_STREAM)[:64]))"
)


def check_deadline(started: float, timeout: float, cancel: Event) -> None:
    if cancel.is_set():
        raise AdapterCancelledError("Benchmark cancelled")
    if perf_counter() - started >= timeout:
        raise AdapterTimeoutError("Runtime request timed out")


def _addresses(host: str, port: int, check: Callable[[], None]) -> list[tuple[int, Any]]:
    try:
        address = ip_address(host)
    except ValueError:
        # System DNS may block indefinitely. Isolate just the resolver, never
        # prompts, headers or API keys, and always reap this owned subprocess.
        process = subprocess.Popen(
            [sys.executable, "-I", "-c", _RESOLVE, host, str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            env={
                key: value
                for key, value in os.environ.items()
                if key.upper() in {"SYSTEMROOT", "WINDIR", "PATH"}
            },
        )
        try:
            while True:
                check()
                try:
                    output, _ = process.communicate(timeout=0.05)
                    break
                except subprocess.TimeoutExpired:
                    continue
            check()
            if process.returncode != 0:
                raise OSError("Runtime name resolution failed")
            return [(item[0], tuple(item[4])) for item in json.loads(output)]
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate()
    family = socket.AF_INET6 if address.version == 6 else socket.AF_INET
    return [(family, (host, port))]


def _wait(sock: socket.socket, check: Callable[[], None], *, write: bool) -> None:
    check()
    select.select([] if write else [sock], [sock] if write else [], [], 0.01)


def connect(host: str, port: int, *, tls: bool, check: Callable[[], None]) -> socket.socket:
    """Connect and verify TLS without blocking cancellation on DNS, TCP or TLS."""
    pending = {
        0,
        errno.EINPROGRESS,
        errno.EWOULDBLOCK,
        errno.EALREADY,
        getattr(errno, "WSAEWOULDBLOCK", 10035),
    }
    for family, address in _addresses(host, port, check):
        check()
        sock = socket.socket(family, socket.SOCK_STREAM)
        try:
            sock.setblocking(False)
            result = sock.connect_ex(address)
            if result not in pending:
                raise OSError("Runtime connection failed")
            while result != 0:
                _wait(sock, check, write=True)
                _, ready, _ = select.select([], [sock], [], 0)
                if ready:
                    result = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                    if result:
                        raise OSError("Runtime connection failed")
            if tls:
                sock = ssl.create_default_context().wrap_socket(
                    sock, server_hostname=host, do_handshake_on_connect=False
                )
                assert isinstance(sock, ssl.SSLSocket)
                while True:
                    check()
                    try:
                        sock.do_handshake()
                        break
                    except ssl.SSLWantReadError:
                        _wait(sock, check, write=False)
                    except ssl.SSLWantWriteError:
                        _wait(sock, check, write=True)
            return sock
        except OSError:
            sock.close()
        except BaseException:
            sock.close()
            raise
    raise OSError("Runtime connection failed")


class BoundedConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, *, tls: bool, check: Callable[[], None]) -> None:
        super().__init__(host, port)
        self._tls = tls
        self._check = check

    def connect(self) -> None:
        self.sock = connect(self.host, self.port, tls=self._tls, check=self._check)

    def send(self, data: Any) -> None:
        if self.sock is None:
            self.connect()
        assert self.sock is not None
        remaining = memoryview(data)
        while remaining:
            self._check()
            try:
                sent = self.sock.send(remaining[:65536])
            except BlockingIOError, ssl.SSLWantWriteError:
                _wait(self.sock, self._check, write=True)
                continue
            except ssl.SSLWantReadError:
                _wait(self.sock, self._check, write=False)
                continue
            if sent == 0:
                raise OSError("Runtime connection closed")
            remaining = remaining[sent:]
