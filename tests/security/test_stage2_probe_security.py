from __future__ import annotations

import socket
from pathlib import Path

from flopbench.contracts import PrivacyLevel
from flopbench.probe.providers import SafeFallbackProvider
from flopbench.probe.service import canonical_probe_json, run_fixture_probe, run_live_probe

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "fixtures" / "hardware"


def test_s2_t06_public_report_has_zero_sensitive_field_leakage() -> None:
    report = run_fixture_probe(HARDWARE / "secret-leak-trap.json", PrivacyLevel.PUBLIC)
    serialized = canonical_probe_json(report)

    for secret in (
        "SECRET-HOSTNAME",
        "SECRET-USERNAME",
        "192.0.2.99",
        "TOKEN-secret-value",
        "BEGIN PRIVATE KEY",
        "SECRET-DEVICE",
        "SECRET-PCI-ID",
        "SECRET-SERIAL",
        "SECRET-OS-BUILD",
    ):
        assert secret not in serialized


def test_s2_t07_live_probe_opens_no_network_connection(monkeypatch: object) -> None:
    calls: list[object] = []

    def blocked(*args: object, **kwargs: object) -> None:
        calls.append((args, kwargs))
        raise AssertionError("network access is forbidden during probe")

    monkeypatch.setattr(socket, "create_connection", blocked)  # type: ignore[attr-defined]
    monkeypatch.setattr(socket.socket, "connect", blocked)  # type: ignore[attr-defined]

    run_live_probe(PrivacyLevel.PUBLIC, SafeFallbackProvider())

    assert calls == []
