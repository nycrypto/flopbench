"""Additive export contract; existing report schemas remain immutable."""

from __future__ import annotations

from typing import Annotated, Literal, Self

from pydantic import Field, StrictStr, model_validator

from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import (
    BenchmarkReport,
    PrivacyLevel,
    ProfileReference,
    ReadinessReport,
    SemVer,
    Sha256Hex,
    StrictModel,
)
from flopbench.probe.models import ProbeReport
from flopbench.reporting.canonical import canonical_digest
from flopbench.validator_doctor.models import ValidatorDoctorReport

type ReportPayload = Annotated[
    ReadinessReport | BenchmarkReport | BenchmarkReportV2 | ProbeReport | ValidatorDoctorReport,
    Field(discriminator="schema_id"),
]
FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]


class ReportProvenance(StrictModel):
    exporter_version: SemVer
    source_tool_version: SemVer
    redaction_policy: Literal["1.0.0"] = "1.0.0"
    canonicalizer: Literal["rfc8785/0.1.4"] = "rfc8785/0.1.4"
    source_jcs_sha256: Sha256Hex | None
    profile_binding: Literal["source-report", "user-selected", "none"]
    authenticity: Literal["unverified-local-observations"] = "unverified-local-observations"


class ReportDocument(StrictModel):
    schema_id: Literal["flopbench-report-document-v1"] = Field(alias="schema")
    privacy_level: PrivacyLevel
    payload: ReportPayload
    comparison_profile: ProfileReference | None
    provenance: ReportProvenance

    @model_validator(mode="after")
    def consistent_context(self) -> Self:
        if (
            self.privacy_level is not PrivacyLevel.PRIVATE
            and self.provenance.source_jcs_sha256 is not None
        ):
            raise ValueError("shared reports must not fingerprint private source data")
        if self.provenance.source_tool_version != self.payload.tool_version:
            raise ValueError("source tool version must match the redacted payload")
        if isinstance(self.payload, ReadinessReport):
            if (
                self.comparison_profile != self.payload.profile
                or self.provenance.profile_binding != "source-report"
            ):
                raise ValueError("readiness profile must come from the source report")
            if self.payload.environment.privacy_level != self.privacy_level:
                raise ValueError("readiness privacy must match document")
        elif self.provenance.profile_binding != (
            "user-selected" if self.comparison_profile else "none"
        ):
            raise ValueError("profile binding must describe its origin")
        if (
            isinstance(self.payload, ProbeReport)
            and self.payload.privacy_level != self.privacy_level
        ):
            raise ValueError("probe privacy must match document")
        return self


class ReportDigest(StrictModel):
    algorithm: Literal["sha256"] = "sha256"
    canonicalization: Literal["jcs-rfc8785"] = "jcs-rfc8785"
    scope: Literal["document"] = "document"
    value: Sha256Hex


class ReportExport(StrictModel):
    schema_id: Literal["flopbench-report-export-v1"] = Field(alias="schema")
    document: ReportDocument
    digest: ReportDigest

    @model_validator(mode="after")
    def digest_matches_document(self) -> Self:
        expected = canonical_digest(self.document.model_dump(mode="json", by_alias=True))
        if expected != self.digest.value:
            raise ValueError("document digest mismatch")
        return self


class ReportChange(StrictModel):
    path: StrictStr
    kind: Literal["added", "removed", "changed"]
    before: object | None = None
    after: object | None = None


class ReportDiff(StrictModel):
    schema_id: Literal["flopbench-report-diff-v1"] = Field(alias="schema")
    left_digest: Sha256Hex
    right_digest: Sha256Hex
    truncated: bool
    changes: list[ReportChange]


class MetricComparison(StrictModel):
    metric: Literal["ttft", "tokens_per_second", "latency", "peak_vram"]
    unit: StrictStr
    left_p50: FiniteFloat | None
    right_p50: FiniteFloat | None
    absolute_delta: FiniteFloat | None
    relative_delta_percent: FiniteFloat | None


class BenchmarkComparison(StrictModel):
    schema_id: Literal["flopbench-benchmark-comparison-v1"] = Field(alias="schema")
    compatible: bool
    reason_codes: list[StrictStr]
    left_digest: Sha256Hex
    right_digest: Sha256Hex
    metrics: list[MetricComparison]
