"""Composition and redaction for local passive probes."""

from __future__ import annotations

import getpass
import json
import platform
import shutil
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from uuid import uuid4

import psutil  # type: ignore[import-untyped]
from pydantic import ValidationError

from flopbench import __version__
from flopbench.contracts import PrivacyLevel
from flopbench.probe.models import (
    CpuInfo,
    DiskInfo,
    DiskKind,
    GpuProbe,
    HostDetails,
    MemoryInfo,
    ProbeFixture,
    ProbeReport,
    ProbeSource,
    SystemInfo,
)
from flopbench.probe.privacy import public_report
from flopbench.probe.providers import GpuProvider, NvidiaProvider

MAX_FIXTURE_BYTES = 1024 * 1024


class ProbeErrorCode(StrEnum):
    FIXTURE_READ_ERROR = "probe.fixture_read_error"
    FIXTURE_TOO_LARGE = "probe.fixture_too_large"
    FIXTURE_INVALID = "probe.fixture_invalid"
    PROVIDER_MALFORMED = "probe.provider_malformed"
    PROBE_FAILED = "probe.failed"


class ProbeError(RuntimeError):
    """Safe error presented by the CLI without paths or provider payloads."""

    def __init__(self, code: ProbeErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def canonical_probe_json(report: ProbeReport) -> str:
    """Return deterministic JSON with no platform-dependent whitespace."""

    payload = report.model_dump(mode="json", by_alias=True, exclude_none=True)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _validated_gpu(provider: GpuProvider) -> GpuProbe:
    try:
        raw = provider.probe()
    except Exception as exc:
        raise ProbeError(ProbeErrorCode.PROBE_FAILED, "GPU provider failed safely") from exc
    try:
        return GpuProbe.model_validate(raw)
    except ValidationError as exc:
        raise ProbeError(
            ProbeErrorCode.PROVIDER_MALFORMED,
            "GPU provider returned an invalid response",
        ) from exc


def _load_fixture(path: Path) -> ProbeFixture:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ProbeError(ProbeErrorCode.FIXTURE_READ_ERROR, "Fixture could not be read") from exc
    if len(raw) > MAX_FIXTURE_BYTES:
        raise ProbeError(ProbeErrorCode.FIXTURE_TOO_LARGE, "Fixture exceeds the size limit")
    try:
        return ProbeFixture.model_validate_json(raw)
    except (ValidationError, ValueError) as exc:
        raise ProbeError(ProbeErrorCode.FIXTURE_INVALID, "Fixture is invalid") from exc


def run_fixture_probe(path: Path, privacy: PrivacyLevel) -> ProbeReport:
    fixture = _load_fixture(path)

    class FixtureGpuProvider:
        name = "fixture"

        def probe(self) -> object:
            return fixture.gpu

    report = ProbeReport(
        schema="flopbench-probe-v1",
        probe_id=fixture.probe_id,
        captured_at=fixture.captured_at,
        privacy_level=PrivacyLevel.PRIVATE,
        source=ProbeSource.FIXTURE,
        system=fixture.system,
        cpu=fixture.cpu,
        memory=fixture.memory,
        disks=fixture.disks,
        gpu=_validated_gpu(FixtureGpuProvider()),
        tool_version=__version__,
    )
    return public_report(report) if privacy is PrivacyLevel.PUBLIC else report


def _live_disks() -> list[DiskInfo]:
    disks: list[DiskInfo] = []
    seen: set[str] = set()
    for partition in sorted(psutil.disk_partitions(all=False), key=lambda item: item.mountpoint):
        if partition.mountpoint in seen:
            continue
        try:
            usage = psutil.disk_usage(partition.mountpoint)
        except OSError:
            continue
        if usage.total <= 0:
            continue
        seen.add(partition.mountpoint)
        disks.append(
            DiskInfo(
                kind=DiskKind.UNKNOWN,
                total_bytes=usage.total,
                available_bytes=usage.free,
                device=partition.device or None,
                mount_point=partition.mountpoint,
            )
        )
    if not disks:
        usage = shutil.disk_usage(Path.cwd().anchor or Path.cwd())
        disks.append(
            DiskInfo(
                kind=DiskKind.UNKNOWN,
                total_bytes=usage.total,
                available_bytes=usage.free,
                device=None,
                mount_point=str(Path.cwd().anchor or Path.cwd()),
            )
        )
    return disks


def run_live_probe(
    privacy: PrivacyLevel,
    provider: GpuProvider | None = None,
) -> ProbeReport:
    """Collect passive local metrics. This function performs no network calls."""

    virtual_memory = psutil.virtual_memory()
    logical_cores = psutil.cpu_count(logical=True) or 1
    report = ProbeReport(
        schema="flopbench-probe-v1",
        probe_id=uuid4(),
        captured_at=datetime.now(UTC),
        privacy_level=PrivacyLevel.PRIVATE,
        source=ProbeSource.LIVE,
        system=SystemInfo(
            os_family=platform.system() or "unknown",
            architecture=platform.machine() or "unknown",
            os_version=platform.version() or None,
            host=HostDetails(
                hostname=platform.node() or None,
                user_name=getpass.getuser() or None,
                ip_addresses=[],
            ),
        ),
        cpu=CpuInfo(
            logical_cores=logical_cores,
            physical_cores=psutil.cpu_count(logical=False),
            model=platform.processor() or None,
        ),
        memory=MemoryInfo(
            total_bytes=virtual_memory.total, available_bytes=virtual_memory.available
        ),
        disks=_live_disks(),
        gpu=_validated_gpu(provider or NvidiaProvider()),
        tool_version=__version__,
    )
    return public_report(report) if privacy is PrivacyLevel.PUBLIC else report
