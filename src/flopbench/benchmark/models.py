"""Strict public and internal models for inference benchmarking."""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, Strict, StrictBool, StrictStr, model_validator

from flopbench.contracts import MetricConfidence, SemVer, Sha256Hex, StrictModel, _require_utc

NonNegativeFiniteFloat = Annotated[float, Strict(), Field(ge=0, allow_inf_nan=False)]
NonNegativeInt = Annotated[int, Strict(), Field(ge=0)]
PositiveInt = Annotated[int, Strict(), Field(gt=0)]


class BenchmarkOutcome(StrEnum):
    """Every terminal state of one measured request."""

    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class BenchmarkAdapterIdentity(StrictModel):
    """Runtime identity without leaking a full endpoint URL."""

    name: StrictStr
    runtime_version: StrictStr
    endpoint_scope: Literal["none", "loopback", "allowlisted_external"]


class BenchmarkModelIdentity(StrictModel):
    """Model name and immutable content digest."""

    name: StrictStr
    digest_algorithm: Literal["sha256"] = "sha256"
    digest: Sha256Hex


class BenchmarkWorkloadIdentity(StrictModel):
    """Exact versioned workload bytes and execution counts."""

    id: StrictStr
    version: SemVer
    sha256: Sha256Hex
    warmup_runs: NonNegativeInt
    measured_runs: PositiveInt


class BenchmarkRunRecord(StrictModel):
    """Auditable outcome of one warmup or measured request."""

    sequence: PositiveInt
    prompt_id: StrictStr
    warmup: StrictBool
    outcome: BenchmarkOutcome
    ttft_seconds: NonNegativeFiniteFloat | None = None
    latency_seconds: NonNegativeFiniteFloat | None = None
    generated_tokens: NonNegativeInt | None = None
    tokens_per_second: NonNegativeFiniteFloat | None = None
    peak_vram_bytes: NonNegativeInt | None = None
    error_code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]+$")] | None = None
    raw_response_sha256: Sha256Hex | None = None

    @model_validator(mode="after")
    def outcome_fields_are_consistent(self) -> Self:
        metrics = (
            self.ttft_seconds,
            self.latency_seconds,
            self.generated_tokens,
            self.tokens_per_second,
        )
        if self.outcome is BenchmarkOutcome.SUCCESS and any(value is None for value in metrics):
            raise ValueError("successful run requires all core metrics")
        if self.outcome is BenchmarkOutcome.SUCCESS and self.error_code is not None:
            raise ValueError("successful run cannot contain an error code")
        if self.outcome is not BenchmarkOutcome.SUCCESS and self.error_code is None:
            raise ValueError("non-successful run requires an error code")
        if (
            self.ttft_seconds is not None
            and self.latency_seconds is not None
            and self.ttft_seconds > self.latency_seconds
        ):
            raise ValueError("TTFT must not exceed latency")
        return self


class BenchmarkMetricSummary(StrictModel):
    """Raw successful samples plus nearest-rank percentiles."""

    unit: StrictStr
    confidence: MetricConfidence
    samples: list[NonNegativeFiniteFloat]
    p50: NonNegativeFiniteFloat | None
    p95: NonNegativeFiniteFloat | None

    @model_validator(mode="after")
    def percentiles_match_empty_state(self) -> Self:
        if not self.samples and (self.p50 is not None or self.p95 is not None):
            raise ValueError("empty metric samples require null percentiles")
        if self.samples and (self.p50 is None or self.p95 is None):
            raise ValueError("metric samples require p50 and p95")
        if self.samples:
            ordered = sorted(self.samples)
            if (
                self.p50 != ordered[math.ceil(len(ordered) * 0.5) - 1]
                or self.p95 != ordered[math.ceil(len(ordered) * 0.95) - 1]
            ):
                raise ValueError("percentiles must match nearest-rank samples")
        return self


class BenchmarkMetricsV2(StrictModel):
    """Required benchmark summaries."""

    ttft: BenchmarkMetricSummary
    tokens_per_second: BenchmarkMetricSummary
    latency: BenchmarkMetricSummary
    peak_vram: BenchmarkMetricSummary


class BenchmarkOutcomeSummary(StrictModel):
    """Complete measured-run accounting, including partial requests."""

    success: NonNegativeInt
    timeout: NonNegativeInt
    error: NonNegativeInt
    cancelled: NonNegativeInt
    partial: NonNegativeInt
    error_rate: Annotated[float, Strict(), Field(ge=0, le=1, allow_inf_nan=False)]

    @property
    def total(self) -> int:
        return self.success + self.timeout + self.error + self.cancelled + self.partial


class BenchmarkReportV2(StrictModel):
    """Published benchmark-report-v2 contract emitted by Stage 5."""

    schema_id: Literal["flopbench-benchmark-report-v2"] = Field(
        alias="schema", serialization_alias="schema"
    )
    benchmark_id: UUID
    adapter: BenchmarkAdapterIdentity
    model: BenchmarkModelIdentity
    workload: BenchmarkWorkloadIdentity
    runs: list[BenchmarkRunRecord]
    metrics: BenchmarkMetricsV2
    outcomes: BenchmarkOutcomeSummary
    started_at: datetime
    finished_at: datetime
    tool_version: SemVer

    @model_validator(mode="after")
    def report_is_consistent(self) -> Self:
        _require_utc(self.started_at)
        _require_utc(self.finished_at)
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        measured = [run for run in self.runs if not run.warmup]
        total = self.workload.warmup_runs + self.workload.measured_runs
        if len(self.runs) != total or any(
            run.sequence != index + 1 or run.warmup != (index < self.workload.warmup_runs)
            for index, run in enumerate(self.runs)
        ):
            raise ValueError("run sequence and warmup count must match workload")
        if len(measured) != self.workload.measured_runs:
            raise ValueError("measured run count must match workload")
        expected = dict.fromkeys(BenchmarkOutcome, 0)
        for run in measured:
            expected[run.outcome] += 1
        if (
            self.outcomes.success != expected[BenchmarkOutcome.SUCCESS]
            or self.outcomes.timeout != expected[BenchmarkOutcome.TIMEOUT]
            or self.outcomes.error != expected[BenchmarkOutcome.ERROR]
            or self.outcomes.cancelled != expected[BenchmarkOutcome.CANCELLED]
            or self.outcomes.partial != expected[BenchmarkOutcome.PARTIAL]
        ):
            raise ValueError("outcome counters must match measured runs")
        expected_error_rate = (self.outcomes.total - self.outcomes.success) / self.outcomes.total
        if not math.isclose(self.outcomes.error_rate, expected_error_rate, abs_tol=1e-12):
            raise ValueError("error_rate must include every non-success outcome")
        successful = [run for run in measured if run.outcome is BenchmarkOutcome.SUCCESS]
        for summary, field in (
            (self.metrics.ttft, "ttft_seconds"),
            (self.metrics.latency, "latency_seconds"),
            (self.metrics.tokens_per_second, "tokens_per_second"),
            (self.metrics.peak_vram, "peak_vram_bytes"),
        ):
            observed = [
                getattr(run, field) for run in successful if getattr(run, field) is not None
            ]
            if summary.samples != observed:
                raise ValueError("summary samples must match successful measured runs")
        return self
