"""Strict contracts for bounded active validator tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, Strict, StrictStr, field_validator, model_validator

from flopbench.contracts import NonNegativeInt, ReasonCode, ResultStatus, SemVer, StrictModel

NonNegativeFloat = Annotated[float, Strict(), Field(ge=0, allow_inf_nan=False)]
SignedFloat = Annotated[float, Strict(), Field(allow_inf_nan=False)]
Port = Annotated[int, Strict(), Field(ge=1, le=65535)]
Percent = Annotated[float, Strict(), Field(ge=0, le=100, allow_inf_nan=False)]


class TestLimits(StrictModel):
    disk_bytes: Annotated[int, Strict(), Field(ge=1024, le=64 * 1024**2)] = 8 * 1024**2
    disk_chunk_bytes: Annotated[int, Strict(), Field(ge=1024, le=1024**2)] = 1024**2
    max_duration_seconds: Annotated[float, Strict(), Field(gt=0, le=30)] = 10.0
    network_attempts: Annotated[int, Strict(), Field(ge=1, le=20)] = 5
    network_timeout_seconds: Annotated[float, Strict(), Field(gt=0, le=5)] = 2.0

    @model_validator(mode="after")
    def chunk_fits_file(self) -> Self:
        if self.disk_chunk_bytes > self.disk_bytes:
            raise ValueError("disk_chunk_bytes must not exceed disk_bytes")
        return self


class NetworkTarget(StrictModel):
    host: Annotated[str, Field(min_length=1, max_length=253)]
    port: Port

    @field_validator("host")
    @classmethod
    def host_is_plain_name_or_address(cls, value: str) -> str:
        if any(character.isspace() for character in value) or "/" in value or "\\" in value:
            raise ValueError("host must be a plain hostname or IP address")
        return value

    @property
    def display(self) -> str:
        return f"{self.host}:{self.port}"


class DiskTestResult(StrictModel):
    status: ResultStatus
    bytes_tested: NonNegativeInt
    write_bytes_per_second: NonNegativeFloat | None
    read_bytes_per_second: NonNegativeFloat | None
    write_latency_p95_ms: NonNegativeFloat | None
    read_latency_p95_ms: NonNegativeFloat | None
    reason_codes: Annotated[list[ReasonCode], Field(min_length=1)]

    @model_validator(mode="after")
    def completed_status_has_metrics(self) -> Self:
        metrics = (
            self.write_bytes_per_second,
            self.read_bytes_per_second,
            self.write_latency_p95_ms,
            self.read_latency_p95_ms,
        )
        if self.status in {ResultStatus.PASS, ResultStatus.WARN, ResultStatus.FAIL} and (
            self.bytes_tested == 0 or any(metric is None for metric in metrics)
        ):
            raise ValueError("completed disk status requires all metrics")
        return self


class NetworkTestResult(StrictModel):
    status: ResultStatus
    target: StrictStr | None
    attempts: NonNegativeInt
    received: NonNegativeInt
    packet_loss_percent: Percent | None
    latency_p50_ms: NonNegativeFloat | None
    latency_p95_ms: NonNegativeFloat | None
    jitter_p95_ms: NonNegativeFloat | None
    reason_codes: Annotated[list[ReasonCode], Field(min_length=1)]

    @model_validator(mode="after")
    def received_does_not_exceed_attempts(self) -> Self:
        if self.received > self.attempts:
            raise ValueError("received must not exceed attempts")
        metrics = (
            self.packet_loss_percent,
            self.latency_p50_ms,
            self.latency_p95_ms,
            self.jitter_p95_ms,
        )
        if self.status in {ResultStatus.PASS, ResultStatus.WARN, ResultStatus.FAIL} and (
            self.received == 0 or any(metric is None for metric in metrics)
        ):
            raise ValueError("completed network status requires all metrics")
        return self


class ClockTestResult(StrictModel):
    status: ResultStatus
    server: StrictStr | None
    offset_ms: SignedFloat | None
    round_trip_ms: NonNegativeFloat | None
    reason_codes: Annotated[list[ReasonCode], Field(min_length=1)]

    @model_validator(mode="after")
    def completed_status_has_metrics(self) -> Self:
        if self.status in {ResultStatus.PASS, ResultStatus.WARN, ResultStatus.FAIL} and (
            self.offset_ms is None or self.round_trip_ms is None
        ):
            raise ValueError("completed clock status requires all metrics")
        return self


class ValidatorDoctorReport(StrictModel):
    schema_id: Literal["flopbench-validator-doctor-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    doctor_id: UUID
    created_at: datetime
    approved: Literal[True]
    limits: TestLimits
    disk: DiskTestResult
    network: NetworkTestResult
    clock: ClockTestResult
    tool_version: SemVer

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must use UTC")
        return value


class DoctorFixture(StrictModel):
    schema_id: Literal["flopbench-validator-doctor-fixture-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    doctor_id: UUID
    created_at: datetime
    limits: TestLimits
    disk: DiskTestResult
    network: NetworkTestResult
    clock: ClockTestResult

    @field_validator("created_at")
    @classmethod
    def created_at_is_utc(cls, value: datetime) -> datetime:
        if value.utcoffset() != UTC.utcoffset(value):
            raise ValueError("created_at must use UTC")
        return value
