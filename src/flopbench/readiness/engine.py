"""Stage 3 readiness rules over normalized passive-probe data."""

from __future__ import annotations

from collections import Counter
from uuid import NAMESPACE_URL, uuid5

from flopbench import __version__
from flopbench.contracts import (
    EnvironmentSummary,
    MetricConfidence,
    ProfileReference,
    ReadinessCheck,
    ReadinessReport,
    ResultStatus,
    ResultSummary,
    Role,
)
from flopbench.probe.models import DiskKind, GpuStatus, ProbeReport
from flopbench.profile_loader import LoadedProfile


def _numeric_check(
    *,
    code: str,
    actual: int | None,
    threshold: int,
    unit: str,
    pass_reason: str,
    fail_reason: str,
    unknown_reason: str,
) -> ReadinessCheck:
    if actual is None:
        status = ResultStatus.UNKNOWN
        reason = unknown_reason
    elif actual >= threshold:
        status = ResultStatus.PASS
        reason = pass_reason
    else:
        status = ResultStatus.FAIL
        reason = fail_reason
    return ReadinessCheck(
        code=code,
        status=status,
        source_kind="source_profile",
        required=True,
        actual=actual,
        threshold=threshold,
        unit=unit,
        confidence=MetricConfidence.REPORTED,
        reason_codes=[reason],
    )


def _miner_checks(probe: ProbeReport, profile: LoadedProfile) -> list[ReadinessCheck]:
    threshold = profile.profile.parameters.miner.recommended_vram_bytes
    actual: int | None = None
    source_status = ResultStatus.UNKNOWN
    source_reason = "miner.vram_unknown"

    if probe.gpu.status is GpuStatus.DETECTED:
        values = [device.vram_total_bytes for device in probe.gpu.devices]
        known_values = [value for value in values if value is not None]
        if known_values:
            actual = max(known_values)
            if actual >= threshold:
                source_status = ResultStatus.PASS
                source_reason = "miner.vram_meets_source_threshold"
            else:
                source_status = ResultStatus.FAIL
                source_reason = "miner.vram_below_source_threshold"
    elif probe.gpu.status is GpuStatus.UNSUPPORTED:
        source_status = ResultStatus.UNSUPPORTED
        source_reason = "miner.gpu_provider_unsupported"
    elif probe.gpu.status is GpuStatus.NO_SUPPORTED_GPU:
        source_status = ResultStatus.FAIL
        source_reason = "miner.no_supported_gpu"

    source_check = ReadinessCheck(
        code="miner.vram_bytes",
        status=source_status,
        source_kind="source_profile",
        required=True,
        actual=actual,
        threshold=threshold,
        unit="byte",
        confidence=MetricConfidence.REPORTED,
        reason_codes=[source_reason],
    )

    headroom_threshold = threshold + threshold // 4
    if actual is None:
        community_status = (
            ResultStatus.UNSUPPORTED
            if probe.gpu.status is GpuStatus.UNSUPPORTED
            else ResultStatus.UNKNOWN
        )
        community_reason = "community.miner.vram_headroom_unknown"
    elif actual < threshold:
        community_status = ResultStatus.FAIL
        community_reason = "community.miner.vram_below_source_threshold"
    elif actual < headroom_threshold:
        community_status = ResultStatus.WARN
        community_reason = "community.miner.vram_low_headroom"
    else:
        community_status = ResultStatus.PASS
        community_reason = "community.miner.vram_headroom_ok"

    community_check = ReadinessCheck(
        code="community.miner.vram_headroom",
        status=community_status,
        source_kind="community",
        required=False,
        actual=actual,
        threshold=headroom_threshold,
        unit="byte",
        confidence=MetricConfidence.DERIVED,
        reason_codes=[community_reason],
    )
    return [source_check, community_check]


def _validator_checks(probe: ProbeReport, profile: LoadedProfile) -> list[ReadinessCheck]:
    parameters = profile.profile.parameters.validator
    largest_disk = max(probe.disks, key=lambda disk: disk.total_bytes, default=None)
    checks = [
        _numeric_check(
            code="validator.cpu_physical_cores",
            actual=probe.cpu.physical_cores,
            threshold=parameters.recommended_cpu_cores,
            unit="core",
            pass_reason="validator.cpu_meets_source_threshold",
            fail_reason="validator.cpu_below_source_threshold",
            unknown_reason="validator.cpu_physical_cores_unknown",
        ),
        _numeric_check(
            code="validator.memory_bytes",
            actual=probe.memory.total_bytes,
            threshold=parameters.recommended_memory_bytes,
            unit="byte",
            pass_reason="validator.memory_meets_source_threshold",
            fail_reason="validator.memory_below_source_threshold",
            unknown_reason="validator.memory_unknown",
        ),
        _numeric_check(
            code="validator.disk_capacity_bytes",
            actual=largest_disk.total_bytes if largest_disk else None,
            threshold=parameters.recommended_nvme_bytes,
            unit="byte",
            pass_reason="validator.disk_capacity_meets_source_threshold",
            fail_reason="validator.disk_capacity_below_source_threshold",
            unknown_reason="validator.disk_capacity_unknown",
        ),
    ]

    if largest_disk is None or largest_disk.kind is DiskKind.UNKNOWN:
        disk_status = ResultStatus.UNKNOWN
        disk_actual = None if largest_disk is None else largest_disk.kind.value
        disk_reason = "validator.disk_kind_unknown"
    elif largest_disk.kind is DiskKind.NVME:
        disk_status = ResultStatus.PASS
        disk_actual = largest_disk.kind.value
        disk_reason = "validator.disk_kind_nvme"
    else:
        disk_status = ResultStatus.FAIL
        disk_actual = largest_disk.kind.value
        disk_reason = "validator.disk_kind_not_nvme"
    checks.append(
        ReadinessCheck(
            code="validator.disk_kind",
            status=disk_status,
            source_kind="source_profile",
            required=True,
            actual=disk_actual,
            threshold=DiskKind.NVME.value,
            unit=None,
            confidence=MetricConfidence.REPORTED,
            reason_codes=[disk_reason],
        )
    )
    checks.append(
        ReadinessCheck(
            code="validator.network_bits_per_second",
            status=ResultStatus.SKIPPED,
            source_kind="source_profile",
            required=True,
            actual=None,
            threshold=parameters.recommended_network_bits_per_second,
            unit="bit/s",
            confidence=MetricConfidence.REPORTED,
            reason_codes=["validator.network_active_test_not_run"],
        )
    )
    return checks


def _summary(checks: list[ReadinessCheck]) -> ResultSummary:
    counts = Counter(check.status for check in checks)
    return ResultSummary(
        **{
            "pass": counts[ResultStatus.PASS],
            "warn": counts[ResultStatus.WARN],
            "fail": counts[ResultStatus.FAIL],
            "unknown": counts[ResultStatus.UNKNOWN],
            "skipped": counts[ResultStatus.SKIPPED],
            "unsupported": counts[ResultStatus.UNSUPPORTED],
        }
    )


def evaluate_readiness(
    probe: ProbeReport,
    profile: LoadedProfile,
    role: Role,
) -> ReadinessReport:
    """Evaluate one role without rounding or merging source/community labels."""

    checks = (
        _miner_checks(probe, profile) if role is Role.MINER else _validator_checks(probe, profile)
    )
    report_id = uuid5(
        NAMESPACE_URL,
        f"flopbench:{probe.probe_id}:{profile.sha256}:{role.value}",
    )
    return ReadinessReport(
        schema="flopbench-readiness-report-v1",
        report_id=report_id,
        role=role,
        profile=ProfileReference(
            id=profile.profile.id,
            sha256=profile.sha256,
            source_status=profile.profile.source_status,
        ),
        environment=EnvironmentSummary(
            os_family=probe.system.os_family,
            architecture=probe.system.architecture,
            privacy_level=probe.privacy_level,
        ),
        checks=checks,
        summary=_summary(checks),
        created_at=probe.captured_at,
        tool_version=__version__,
    )
