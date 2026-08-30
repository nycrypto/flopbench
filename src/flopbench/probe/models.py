"""Strict models for passive probe input and output."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import Field, StrictStr, field_validator, model_validator

from flopbench.contracts import (
    NonNegativeInt,
    PositiveInt,
    PrivacyLevel,
    SemVer,
    StrictModel,
)


class ProbeSource(StrEnum):
    LIVE = "live"
    FIXTURE = "fixture"


class DiskKind(StrEnum):
    NVME = "nvme"
    SSD = "ssd"
    HDD = "hdd"
    UNKNOWN = "unknown"


class GpuStatus(StrEnum):
    DETECTED = "detected"
    NO_SUPPORTED_GPU = "no-supported-gpu"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


class HostDetails(StrictModel):
    """Private-only host identifiers."""

    hostname: StrictStr | None = None
    user_name: StrictStr | None = None
    ip_addresses: list[StrictStr] = Field(default_factory=list)


class SystemInfo(StrictModel):
    os_family: StrictStr
    architecture: StrictStr
    os_version: StrictStr | None = None
    host: HostDetails | None = None


class CpuInfo(StrictModel):
    logical_cores: PositiveInt
    physical_cores: PositiveInt | None
    model: StrictStr | None = None


class MemoryInfo(StrictModel):
    total_bytes: PositiveInt
    available_bytes: NonNegativeInt

    @model_validator(mode="after")
    def available_does_not_exceed_total(self) -> Self:
        if self.available_bytes > self.total_bytes:
            raise ValueError("available_bytes must not exceed total_bytes")
        return self


class DiskInfo(StrictModel):
    kind: DiskKind
    total_bytes: PositiveInt
    available_bytes: NonNegativeInt
    device: StrictStr | None = None
    mount_point: StrictStr | None = None

    @model_validator(mode="after")
    def available_does_not_exceed_total(self) -> Self:
        if self.available_bytes > self.total_bytes:
            raise ValueError("available_bytes must not exceed total_bytes")
        return self


class GpuDevice(StrictModel):
    vendor: StrictStr
    name: StrictStr
    vram_total_bytes: PositiveInt | None
    driver_version: StrictStr | None = None
    pci_bus_id: StrictStr | None = None
    serial_number: StrictStr | None = None


class GpuProbe(StrictModel):
    provider: StrictStr
    status: GpuStatus
    devices: list[GpuDevice]
    reason_codes: list[StrictStr]

    @model_validator(mode="after")
    def status_matches_devices(self) -> Self:
        if self.status is GpuStatus.DETECTED and not self.devices:
            raise ValueError("detected status requires at least one device")
        if self.status is not GpuStatus.DETECTED and self.devices:
            raise ValueError("non-detected status cannot include devices")
        return self


class ProbeReport(StrictModel):
    schema_id: Literal["flopbench-probe-v1"] = Field(alias="schema", serialization_alias="schema")
    probe_id: UUID
    captured_at: datetime
    privacy_level: PrivacyLevel
    source: ProbeSource
    system: SystemInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disks: list[DiskInfo]
    gpu: GpuProbe
    tool_version: SemVer

    @field_validator("captured_at")
    @classmethod
    def captured_at_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("captured_at must use UTC")
        return value


class ProbeFixture(StrictModel):
    """Deterministic passive-probe fixture; GPU stays raw for provider validation."""

    schema_id: Literal["flopbench-probe-fixture-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    probe_id: UUID
    captured_at: datetime
    system: SystemInfo
    cpu: CpuInfo
    memory: MemoryInfo
    disks: list[DiskInfo]
    gpu: Any

    @field_validator("captured_at")
    @classmethod
    def captured_at_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("captured_at must use UTC")
        return value
