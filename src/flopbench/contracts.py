"""Versioned Stage 1 data contracts.

The Pydantic models are the single source used to publish the JSON Schemas in
``schemas/``.  Domain measurements use normalized base units: bytes for
capacity and bits per second for network throughput.
"""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    Strict,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

PositiveInt = Annotated[int, Strict(), Field(gt=0)]
NonNegativeInt = Annotated[int, Strict(), Field(ge=0)]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
SemVer = Annotated[
    str,
    Field(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?$"),
]


class StrictModel(BaseModel):
    """Shared behavior for public contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class ProfileStatus(StrEnum):
    """Maturity assigned by the upstream source."""

    DRAFT = "draft"
    PROVISIONAL = "provisional"
    FINAL = "final"


class ResultStatus(StrEnum):
    """Complete set of readiness result states."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    UNKNOWN = "unknown"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


class MetricConfidence(StrEnum):
    """How a metric value was obtained."""

    MEASURED = "measured"
    REPORTED = "reported"
    DERIVED = "derived"
    ESTIMATED = "estimated"
    SIMULATED = "simulated"


class PrivacyLevel(StrEnum):
    """Intended disclosure level for a report."""

    PRIVATE = "private"
    SUPPORT = "support"
    PUBLIC = "public"


class Role(StrEnum):
    """FLOP participant role evaluated by a readiness report."""

    MINER = "miner"
    VALIDATOR = "validator"


class MinerParameters(StrictModel):
    """Normalized miner recommendations from a source profile."""

    recommended_vram_bytes: PositiveInt
    source_text: StrictStr


class ValidatorParameters(StrictModel):
    """Normalized validator recommendations from a source profile."""

    recommended_cpu_cores: PositiveInt
    recommended_memory_bytes: PositiveInt
    recommended_nvme_bytes: PositiveInt
    recommended_network_bits_per_second: PositiveInt
    source_text: StrictStr


class ProfileParameters(StrictModel):
    """Role-specific recommendations."""

    miner: MinerParameters
    validator: ValidatorParameters


class SourceProfile(StrictModel):
    """A versioned, attributable snapshot of upstream requirements."""

    schema_id: Literal["flopbench-source-profile-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    id: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")]
    source_url: AnyHttpUrl
    source_version: StrictStr
    source_status: ProfileStatus
    retrieved_at: date
    source_updated_at: date
    provisional_notice: StrictStr
    parameters: ProfileParameters

    @model_validator(mode="after")
    def retrieved_after_source_update(self) -> Self:
        """A snapshot cannot predate the source revision it records."""

        if self.retrieved_at < self.source_updated_at:
            raise ValueError("retrieved_at must not precede source_updated_at")
        return self


class ProfileReference(StrictModel):
    """Immutable link from a report to its exact source profile bytes."""

    id: StrictStr
    sha256: Sha256Hex
    source_status: ProfileStatus


class EnvironmentSummary(StrictModel):
    """Non-sensitive execution context included in readiness output."""

    os_family: StrictStr
    architecture: StrictStr
    privacy_level: PrivacyLevel


ScalarValue = StrictBool | StrictInt | StrictFloat | StrictStr
ReasonCode = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]+$")]


class ReadinessCheck(StrictModel):
    """One explicit readiness rule outcome."""

    code: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]+$")]
    status: ResultStatus
    source_kind: Literal["source_profile", "community"]
    required: StrictBool
    actual: ScalarValue | None
    threshold: ScalarValue | None
    unit: StrictStr | None
    confidence: MetricConfidence
    reason_codes: Annotated[list[ReasonCode], Field(min_length=1)]


class ResultSummary(StrictModel):
    """Counters for every supported result state; no state may be omitted."""

    pass_: NonNegativeInt = Field(alias="pass", serialization_alias="pass")
    warn: NonNegativeInt
    fail: NonNegativeInt
    unknown: NonNegativeInt
    skipped: NonNegativeInt
    unsupported: NonNegativeInt

    @property
    def total(self) -> int:
        """Return the number of classified checks."""

        return self.pass_ + self.warn + self.fail + self.unknown + self.skipped + self.unsupported


def _require_utc(value: datetime) -> datetime:
    if value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must use UTC")
    return value


class ReadinessReport(StrictModel):
    """Published readiness-report-v1 contract."""

    schema_id: Literal["flopbench-readiness-report-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    report_id: UUID
    role: Role
    profile: ProfileReference
    environment: EnvironmentSummary
    checks: list[ReadinessCheck]
    summary: ResultSummary
    created_at: datetime
    tool_version: SemVer

    _created_at_utc = field_validator("created_at")(_require_utc)

    @model_validator(mode="after")
    def summary_matches_checks(self) -> Self:
        """Prevent internally inconsistent reports."""

        if self.summary.total != len(self.checks):
            raise ValueError("summary total must equal the number of checks")
        counts = Counter(check.status for check in self.checks)
        expected = {
            ResultStatus.PASS: self.summary.pass_,
            ResultStatus.WARN: self.summary.warn,
            ResultStatus.FAIL: self.summary.fail,
            ResultStatus.UNKNOWN: self.summary.unknown,
            ResultStatus.SKIPPED: self.summary.skipped,
            ResultStatus.UNSUPPORTED: self.summary.unsupported,
        }
        if any(counts[status] != count for status, count in expected.items()):
            raise ValueError("summary counters must match check statuses")
        return self


class ModelIdentity(StrictModel):
    """Model name and immutable content identity."""

    name: StrictStr
    digest_algorithm: Literal["sha256"]
    digest: Sha256Hex


class BenchmarkWorkload(StrictModel):
    """Deterministic benchmark input description."""

    id: StrictStr
    prompt_set_sha256: Sha256Hex
    warmup_runs: NonNegativeInt
    measured_runs: PositiveInt


class MetricSeries(StrictModel):
    """Raw samples for one benchmark metric."""

    unit: StrictStr
    confidence: MetricConfidence
    samples: Annotated[list[StrictFloat], Field(min_length=1)]


class BenchmarkMetrics(StrictModel):
    """Required benchmark metric series."""

    ttft: MetricSeries
    tokens_per_second: MetricSeries
    latency: MetricSeries


class BenchmarkFailures(StrictModel):
    """Explicit failed-run accounting."""

    timeout: NonNegativeInt
    error: NonNegativeInt
    cancelled: NonNegativeInt


class BenchmarkReport(StrictModel):
    """Published benchmark-report-v1 contract."""

    schema_id: Literal["flopbench-benchmark-report-v1"] = Field(
        alias="schema", serialization_alias="schema"
    )
    benchmark_id: UUID
    adapter: StrictStr
    model: ModelIdentity
    workload: BenchmarkWorkload
    metrics: BenchmarkMetrics
    failures: BenchmarkFailures
    started_at: datetime
    finished_at: datetime
    tool_version: SemVer

    _started_at_utc = field_validator("started_at")(_require_utc)
    _finished_at_utc = field_validator("finished_at")(_require_utc)

    @model_validator(mode="after")
    def finished_after_start(self) -> Self:
        """Reject a negative benchmark duration."""

        if self.finished_at < self.started_at:
            raise ValueError("finished_at must not precede started_at")
        return self


class Receipt(StrictModel):
    """Published receipt-v1 envelope with an external Ed25519 signature."""

    schema_id: Literal["flopbench-receipt-v1"] = Field(alias="schema", serialization_alias="schema")
    report_schema: Literal["flopbench-readiness-report-v1", "flopbench-benchmark-report-v1"]
    report_sha256: Sha256Hex
    did: Annotated[str, Field(pattern=r"^did:key:z[1-9A-HJ-NP-Za-km-z]+$")]
    canonicalization: Literal["jcs-rfc8785"]
    signature_algorithm: Literal["Ed25519"]
    signature: Annotated[str, Field(min_length=86, max_length=86, pattern=r"^[A-Za-z0-9_-]+$")]
    signed_at: datetime

    _signed_at_utc = field_validator("signed_at")(_require_utc)
