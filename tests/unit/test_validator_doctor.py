from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.clock import ClockAdapter, run_clock_test
from flopbench.validator_doctor.disk import run_disk_test
from flopbench.validator_doctor.metrics import jitter_samples, nearest_rank
from flopbench.validator_doctor.models import (
    NetworkTarget,
    NetworkTestResult,
)
from flopbench.validator_doctor.models import (
    TestLimits as DoctorLimits,
)
from flopbench.validator_doctor.network import NetworkAdapter, run_network_test
from flopbench.validator_doctor.service import (
    DoctorError,
    DoctorErrorCode,
    run_fixture_doctor,
    run_live_doctor,
)

ROOT = Path(__file__).resolve().parents[2]
DOCTOR_FIXTURES = ROOT / "fixtures" / "doctor"


def test_nearest_rank_and_jitter_are_deterministic() -> None:
    assert nearest_rank([40.0, 10.0, 30.0, 20.0], 50) == 20.0
    assert nearest_rank([40.0, 10.0, 30.0, 20.0], 95) == 40.0
    assert jitter_samples([10.0, 30.0, 20.0]) == [20.0, 10.0]


@pytest.mark.parametrize(
    ("values", "percentile", "message"),
    [
        ([], 95, "at least one sample"),
        ([1.0], 0, "percentile must"),
        ([1.0], 101, "percentile must"),
    ],
)
def test_nearest_rank_rejects_invalid_input(
    values: list[float], percentile: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        nearest_rank(values, percentile)


def test_limits_reject_excessive_resources() -> None:
    with pytest.raises(ValidationError):
        DoctorLimits(disk_bytes=64 * 1024**2 + 1)
    with pytest.raises(ValidationError):
        DoctorLimits(disk_bytes=1024, disk_chunk_bytes=2048)


def test_network_target_rejects_paths_and_invalid_ports() -> None:
    with pytest.raises(ValidationError):
        NetworkTarget(host="example.test/path", port=443)
    with pytest.raises(ValidationError):
        NetworkTarget(host="example.test", port=0)


def test_network_result_rejects_impossible_receive_count() -> None:
    with pytest.raises(ValidationError):
        NetworkTestResult(
            status=ResultStatus.PASS,
            target="fixture:443",
            attempts=1,
            received=2,
            packet_loss_percent=0.0,
            latency_p50_ms=1.0,
            latency_p95_ms=1.0,
            jitter_p95_ms=0.0,
            reason_codes=["doctor.network.connection_stable"],
        )


def test_disk_test_uses_and_cleans_isolated_directory(tmp_path: Path) -> None:
    result = run_disk_test(
        DoctorLimits(disk_bytes=64 * 1024, disk_chunk_bytes=4096), temp_root=tmp_path
    )

    assert result.bytes_tested == 64 * 1024
    assert result.write_bytes_per_second is not None
    assert result.read_bytes_per_second is not None
    assert list(tmp_path.iterdir()) == []


class SequenceNetworkAdapter(NetworkAdapter):
    def __init__(self, values: list[float | None]) -> None:
        self.values = iter(values)

    def sample(self, target: NetworkTarget, timeout_seconds: float) -> float | None:
        del target, timeout_seconds
        return next(self.values)


@pytest.mark.parametrize(
    ("values", "status"),
    [
        ([10.0, 10.0, 10.0], ResultStatus.PASS),
        ([10.0, None, 10.0], ResultStatus.WARN),
        ([10.0, None, None], ResultStatus.FAIL),
    ],
)
def test_network_status_boundaries(values: list[float | None], status: ResultStatus) -> None:
    result = run_network_test(
        NetworkTarget(host="fixture.test", port=443),
        DoctorLimits(network_attempts=3),
        adapter=SequenceNetworkAdapter(values),
    )

    assert result.status is status


class FixedClockAdapter(ClockAdapter):
    def __init__(self, offset_ms: float) -> None:
        self.offset_ms = offset_ms

    def sample(self, server: str, timeout_seconds: float) -> tuple[float, float] | None:
        del server, timeout_seconds
        return self.offset_ms, 10.0


@pytest.mark.parametrize(
    ("offset", "status"),
    [(20.0, ResultStatus.PASS), (200.0, ResultStatus.WARN), (1200.0, ResultStatus.FAIL)],
)
def test_clock_status_boundaries(offset: float, status: ResultStatus) -> None:
    assert run_clock_test("fixture.test", 1.0, adapter=FixedClockAdapter(offset)).status is status


def test_service_rejects_missing_approval_before_any_work(tmp_path: Path) -> None:
    with pytest.raises(DoctorError) as caught:
        run_live_doctor(approved=False, limits=DoctorLimits(), temp_root=tmp_path)

    assert caught.value.code is DoctorErrorCode.APPROVAL_REQUIRED
    assert list(tmp_path.iterdir()) == []


def test_live_service_composes_selected_network_and_clock_tests(tmp_path: Path) -> None:
    report = run_live_doctor(
        approved=True,
        limits=DoctorLimits(
            disk_bytes=4096,
            disk_chunk_bytes=1024,
            network_attempts=3,
        ),
        temp_root=tmp_path,
        network_target=NetworkTarget(host="fixture.test", port=443),
        ntp_server="fixture.test",
        network_adapter=SequenceNetworkAdapter([10.0, 10.0, 10.0]),
        clock_adapter=FixedClockAdapter(20.0),
    )

    assert report.approved is True
    assert report.network.status is ResultStatus.PASS
    assert report.clock.status is ResultStatus.PASS
    assert list(tmp_path.iterdir()) == []


def test_fixture_service_rejects_missing_invalid_and_oversized_files(tmp_path: Path) -> None:
    with pytest.raises(DoctorError) as missing:
        run_fixture_doctor(tmp_path / "missing.json", approved=True)
    assert missing.value.code is DoctorErrorCode.FIXTURE_READ_ERROR

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    with pytest.raises(DoctorError) as malformed:
        run_fixture_doctor(invalid, approved=True)
    assert malformed.value.code is DoctorErrorCode.FIXTURE_INVALID

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(DoctorError) as too_large:
        run_fixture_doctor(oversized, approved=True)
    assert too_large.value.code is DoctorErrorCode.FIXTURE_TOO_LARGE


def test_doctor_cli_fixture_outputs_json_and_terminal() -> None:
    fixture = str(DOCTOR_FIXTURES / "fast-disk.json")
    json_result = CliRunner().invoke(
        app,
        ["doctor", "validator", "--approve", "--fixture", fixture, "--format", "json"],
    )
    terminal_result = CliRunner().invoke(
        app,
        ["doctor", "validator", "--approve", "--fixture", fixture],
    )

    assert json_result.exit_code == terminal_result.exit_code == 0
    assert json.loads(json_result.stdout)["disk"]["status"] == "pass"
    assert "Disk: PASS" in terminal_result.stdout


def test_doctor_cli_reports_safe_fixture_error(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        [
            "doctor",
            "validator",
            "--approve",
            "--fixture",
            str(tmp_path / "missing.json"),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 2
    assert "doctor.fixture_read_error" in result.stderr
    assert str(tmp_path) not in result.stderr


def test_doctor_cli_rejects_malformed_network_target() -> None:
    result = CliRunner().invoke(
        app,
        ["doctor", "validator", "--approve", "--network-target", "not-a-target"],
    )

    assert result.exit_code == 2
    assert "network target must be host:port" in result.stderr
