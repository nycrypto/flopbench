"""Consent gate and composition for Stage 4 active tests."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from flopbench import __version__
from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.clock import ClockAdapter, run_clock_test
from flopbench.validator_doctor.disk import AfterChunk, DiskTestCancelledError, run_disk_test
from flopbench.validator_doctor.models import (
    ClockTestResult,
    DiskTestResult,
    DoctorFixture,
    NetworkTarget,
    NetworkTestResult,
    TestLimits,
    ValidatorDoctorReport,
)
from flopbench.validator_doctor.network import NetworkAdapter, run_network_test

MAX_FIXTURE_BYTES = 1024 * 1024


class DoctorErrorCode(StrEnum):
    APPROVAL_REQUIRED = "doctor.approval_required"
    FIXTURE_READ_ERROR = "doctor.fixture_read_error"
    FIXTURE_TOO_LARGE = "doctor.fixture_too_large"
    FIXTURE_INVALID = "doctor.fixture_invalid"


class DoctorError(RuntimeError):
    def __init__(self, code: DoctorErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _skipped_network(reason: str) -> NetworkTestResult:
    return NetworkTestResult(
        status=ResultStatus.SKIPPED,
        target=None,
        attempts=0,
        received=0,
        packet_loss_percent=None,
        latency_p50_ms=None,
        latency_p95_ms=None,
        jitter_p95_ms=None,
        reason_codes=[reason],
    )


def _skipped_clock(reason: str) -> ClockTestResult:
    return ClockTestResult(
        status=ResultStatus.SKIPPED,
        server=None,
        offset_ms=None,
        round_trip_ms=None,
        reason_codes=[reason],
    )


def run_live_doctor(
    *,
    approved: bool,
    limits: TestLimits,
    temp_root: Path | None = None,
    network_target: NetworkTarget | None = None,
    ntp_server: str | None = None,
    network_adapter: NetworkAdapter | None = None,
    clock_adapter: ClockAdapter | None = None,
    after_disk_chunk: AfterChunk | None = None,
) -> ValidatorDoctorReport:
    """Run bounded active tests only after an explicit approval gate."""

    if not approved:
        raise DoctorError(DoctorErrorCode.APPROVAL_REQUIRED, "Active tests require approval")
    try:
        disk = run_disk_test(limits, temp_root=temp_root, after_chunk=after_disk_chunk)
    except DiskTestCancelledError:
        disk = run_disk_test_cancelled_result()
        network_target = None
        ntp_server = None
        network_reason = "doctor.network.skipped_after_cancellation"
        clock_reason = "doctor.clock.skipped_after_cancellation"
    else:
        network_reason = "doctor.network.target_not_selected"
        clock_reason = "doctor.clock.source_not_selected"
    network = (
        run_network_test(network_target, limits, adapter=network_adapter)
        if network_target is not None
        else _skipped_network(network_reason)
    )
    clock = (
        run_clock_test(ntp_server, limits.network_timeout_seconds, adapter=clock_adapter)
        if ntp_server is not None
        else _skipped_clock(clock_reason)
    )
    return ValidatorDoctorReport(
        schema="flopbench-validator-doctor-v1",
        doctor_id=uuid4(),
        created_at=datetime.now(UTC),
        approved=True,
        limits=limits,
        disk=disk,
        network=network,
        clock=clock,
        tool_version=__version__,
    )


def run_disk_test_cancelled_result() -> DiskTestResult:
    return DiskTestResult(
        status=ResultStatus.SKIPPED,
        bytes_tested=0,
        write_bytes_per_second=None,
        read_bytes_per_second=None,
        write_latency_p95_ms=None,
        read_latency_p95_ms=None,
        reason_codes=["doctor.disk.cancelled"],
    )


def run_fixture_doctor(path: Path, *, approved: bool) -> ValidatorDoctorReport:
    if not approved:
        raise DoctorError(DoctorErrorCode.APPROVAL_REQUIRED, "Active tests require approval")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise DoctorError(DoctorErrorCode.FIXTURE_READ_ERROR, "Fixture could not be read") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise DoctorError(DoctorErrorCode.FIXTURE_TOO_LARGE, "Fixture exceeds the size limit")
    try:
        fixture = DoctorFixture.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise DoctorError(DoctorErrorCode.FIXTURE_INVALID, "Fixture is invalid") from exc
    return ValidatorDoctorReport(
        schema="flopbench-validator-doctor-v1",
        doctor_id=fixture.doctor_id,
        created_at=fixture.created_at,
        approved=True,
        limits=fixture.limits,
        disk=fixture.disk,
        network=fixture.network,
        clock=fixture.clock,
        tool_version=__version__,
    )
