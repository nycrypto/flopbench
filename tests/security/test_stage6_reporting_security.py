from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest

from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import PrivacyLevel, ReadinessReport
from flopbench.probe.models import ProbeReport
from flopbench.probe.service import run_fixture_probe
from flopbench.reporting.errors import ReportError
from flopbench.reporting.redaction import contains_secret_marker, redact_report
from flopbench.reporting.render import render_json
from flopbench.reporting.service import create_export, load_report, write_new_file
from flopbench.validator_doctor.models import ValidatorDoctorReport
from flopbench.validator_doctor.service import run_fixture_doctor

ROOT = Path(__file__).resolve().parents[2]


def test_public_secret_trap_removes_every_identifier() -> None:
    source = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "secret-leak-trap.json",
        PrivacyLevel.PRIVATE,
    )
    rendered = render_json(create_export(source, PrivacyLevel.PUBLIC)).lower()

    for secret in (
        b"secret-hostname",
        b"secret-username",
        b"192.0.2.99",
        b"token-secret-value",
        b"private key",
        b"secret-device",
        b"secret-pci-id",
        b"secret-serial",
        b"secret-os-build",
    ):
        assert secret not in rendered


def test_support_redacts_host_paths_network_and_clock_but_private_rejects_credentials() -> None:
    probe = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "secret-leak-trap.json",
        PrivacyLevel.PRIVATE,
    )
    support = redact_report(probe, PrivacyLevel.SUPPORT)
    assert isinstance(support, ProbeReport)
    assert support.system.host is None
    assert support.system.os_version == "SECRET-OS-BUILD"
    with pytest.raises(ValueError, match="credential"):
        redact_report(probe, PrivacyLevel.PRIVATE)

    doctor = run_fixture_doctor(ROOT / "fixtures" / "doctor" / "fast-disk.json", approved=True)
    private_doctor = redact_report(doctor, PrivacyLevel.PRIVATE)
    shared_doctor = redact_report(doctor, PrivacyLevel.SUPPORT)
    assert isinstance(shared_doctor, ValidatorDoctorReport)
    assert private_doctor is doctor
    assert shared_doctor.network.target is None
    assert shared_doctor.clock.server is None


def test_all_non_probe_report_types_and_unknown_type() -> None:
    readiness = load_report(ROOT / "fixtures" / "reports" / "readiness-valid.json")
    legacy = load_report(ROOT / "fixtures" / "reports" / "benchmark-valid.json")
    current = load_report(ROOT / "fixtures" / "reports" / "benchmark-v2-mock.json")

    public_readiness = redact_report(readiness, PrivacyLevel.PUBLIC)
    assert isinstance(public_readiness, ReadinessReport)
    assert public_readiness.environment.privacy_level is PrivacyLevel.PUBLIC
    assert redact_report(legacy, PrivacyLevel.SUPPORT) is legacy
    assert isinstance(redact_report(current, PrivacyLevel.PRIVATE), BenchmarkReportV2)
    with pytest.raises(TypeError, match="unsupported"):
        redact_report(cast(Any, object()), PrivacyLevel.PUBLIC)


def test_secret_marker_walks_every_supported_container() -> None:
    assert contains_secret_marker("Authorization")
    assert not contains_secret_marker("ordinary value")
    assert contains_secret_marker({"safe": ("API_KEY",)})
    assert contains_secret_marker(["-----BEGIN PRIVATE KEY-----"])
    assert contains_secret_marker("token-secret-value")
    assert contains_secret_marker("sk-1234567890")
    assert contains_secret_marker("wallet seed")
    assert not contains_secret_marker(42)


def test_symbolic_link_input_and_output_are_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "report.json"
    source.write_bytes(b"{}")
    original = Path.is_symlink

    def input_is_symlink(path: Path) -> bool:
        return path == source or original(path)

    monkeypatch.setattr(Path, "is_symlink", input_is_symlink)
    with pytest.raises(ReportError) as caught:
        load_report(source)
    assert caught.value.code == "report.unsafe_input"

    output = tmp_path / "output.json"
    output.write_bytes(b"sentinel")
    with pytest.raises(ReportError) as caught:
        write_new_file(output, b"replacement")
    assert caught.value.code == "report.output_exists"
    assert output.read_bytes() == b"sentinel"
