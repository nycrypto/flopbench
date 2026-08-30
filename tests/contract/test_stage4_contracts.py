from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.clock import ClockAdapter, run_clock_test
from flopbench.validator_doctor.disk import DiskTestCancelledError
from flopbench.validator_doctor.formatters import doctor_json
from flopbench.validator_doctor.models import (
    NetworkTarget,
    ValidatorDoctorReport,
)
from flopbench.validator_doctor.models import (
    TestLimits as DoctorLimits,
)
from flopbench.validator_doctor.network import NetworkAdapter, run_network_test
from flopbench.validator_doctor.service import run_fixture_doctor, run_live_doctor

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures" / "doctor"

pytestmark = pytest.mark.stage4


def _fixture(name: str) -> ValidatorDoctorReport:
    return run_fixture_doctor(FIXTURES / name, approved=True)


def test_s4_t01_fast_disk_fixture_has_normalized_metrics() -> None:
    result = _fixture("fast-disk.json").disk

    assert result.status is ResultStatus.PASS
    assert result.bytes_tested == 8 * 1024**2
    assert result.write_bytes_per_second == 500_000_000.0
    assert result.write_latency_p95_ms == 4.0


def test_s4_t02_slow_disk_explains_warning() -> None:
    result = _fixture("slow-disk.json").disk

    assert result.status is ResultStatus.WARN
    assert result.reason_codes == ["doctor.disk.performance_has_low_margin"]


def test_s4_t03_unwritable_location_is_controlled(tmp_path: Path) -> None:
    report = run_live_doctor(
        approved=True,
        limits=DoctorLimits(disk_bytes=1024, disk_chunk_bytes=1024),
        temp_root=tmp_path / "missing-parent",
    )

    assert report.disk.status is ResultStatus.UNSUPPORTED
    assert report.disk.reason_codes == ["doctor.disk.temp_write_unavailable"]


def test_s4_t04_user_cancellation_starts_no_test(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app,
        ["doctor", "validator", "--temp-root", str(tmp_path)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "nothing was written or sent" in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_s4_t05_interrupted_disk_test_leaves_no_artifact(tmp_path: Path) -> None:
    observed_parent: Path | None = None

    def cancel(_phase: str, _index: int, test_file: Path) -> None:
        nonlocal observed_parent
        observed_parent = test_file.parent
        raise DiskTestCancelledError("fixture cancellation")

    report = run_live_doctor(
        approved=True,
        limits=DoctorLimits(disk_bytes=4096, disk_chunk_bytes=1024),
        temp_root=tmp_path,
        after_disk_chunk=cancel,
    )

    assert report.disk.status is ResultStatus.SKIPPED
    assert observed_parent is not None
    assert not observed_parent.exists()
    assert list(tmp_path.iterdir()) == []


class OfflineNetworkAdapter(NetworkAdapter):
    def sample(self, target: NetworkTarget, timeout_seconds: float) -> float | None:
        del target, timeout_seconds
        return None


def test_s4_t06_offline_network_is_unknown() -> None:
    result = run_network_test(
        NetworkTarget(host="offline.invalid", port=443),
        DoctorLimits(network_attempts=3),
        adapter=OfflineNetworkAdapter(),
    )

    assert result.status is ResultStatus.UNKNOWN
    assert result.packet_loss_percent == 100.0


class JitterNetworkAdapter(NetworkAdapter):
    def __init__(self) -> None:
        self.samples = iter([10.0, 130.0, 10.0, 130.0, 10.0])

    def sample(self, target: NetworkTarget, timeout_seconds: float) -> float | None:
        del target, timeout_seconds
        return next(self.samples)


def test_s4_t07_high_jitter_uses_nearest_rank_p95_and_warns() -> None:
    result = run_network_test(
        NetworkTarget(host="fixture.example", port=443),
        DoctorLimits(network_attempts=5),
        adapter=JitterNetworkAdapter(),
    )

    assert result.jitter_p95_ms == 120.0
    assert result.status is ResultStatus.WARN


class OfflineClockAdapter(ClockAdapter):
    def sample(self, server: str, timeout_seconds: float) -> tuple[float, float] | None:
        del server, timeout_seconds
        return None


def test_s4_t08_unreachable_ntp_source_is_not_success() -> None:
    result = run_clock_test("offline.invalid", 0.1, adapter=OfflineClockAdapter())

    assert result.status is ResultStatus.UNKNOWN
    assert result.offset_ms is None


def test_doctor_fixture_json_is_deterministic_and_matches_schema() -> None:
    first = doctor_json(_fixture("high-jitter.json"))
    second = doctor_json(_fixture("high-jitter.json"))
    schema = json.loads((ROOT / "schemas" / "validator-doctor-v1.schema.json").read_text())

    assert first == second
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(json.loads(first))


def test_consent_prompt_displays_targets_and_transmitted_data() -> None:
    result = CliRunner().invoke(
        app,
        [
            "doctor",
            "validator",
            "--network-target",
            "127.0.0.1:443",
            "--ntp-server",
            "127.0.0.1",
        ],
        input="n\n",
    )

    assert "TCP connect only to 127.0.0.1:443; no application payload" in result.stdout
    assert "48-byte NTP query to 127.0.0.1" in result.stdout
