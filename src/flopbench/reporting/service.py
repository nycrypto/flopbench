"""Safe loading and deterministic construction of report exports."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import ValidationError

from flopbench import __version__
from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import BenchmarkReport, PrivacyLevel, ProfileReference, ReadinessReport
from flopbench.probe.models import ProbeReport
from flopbench.profile_loader import LoadedProfile
from flopbench.validator_doctor.models import ValidatorDoctorReport

from .canonical import canonical_digest, parse_json
from .errors import ReportError
from .models import ReportDigest, ReportDocument, ReportExport, ReportPayload, ReportProvenance
from .redaction import redact_report

MAX_REPORT_BYTES = 8 * 1024 * 1024


def load_report(path: Path, *, max_bytes: int = MAX_REPORT_BYTES) -> ReportPayload:
    """Read one regular, non-symlink report with bounded memory."""

    try:
        if path.is_symlink() or not path.is_file():
            raise ReportError("report.unsafe_input", "Report input must be a regular file")
        size = path.stat().st_size
        if size > max_bytes:
            raise ReportError("report.too_large", "Report exceeds the size limit")
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except ReportError:
        raise
    except OSError as exc:
        raise ReportError("report.read_error", "Report could not be read") from exc
    if len(raw) > max_bytes:
        raise ReportError("report.too_large", "Report exceeds the size limit")
    data = parse_json(raw)
    schema = data.get("schema")
    try:
        if schema == "flopbench-readiness-report-v1":
            return ReadinessReport.model_validate(data)
        if schema == "flopbench-benchmark-report-v1":
            return BenchmarkReport.model_validate(data)
        if schema == "flopbench-benchmark-report-v2":
            return BenchmarkReportV2.model_validate(data)
        if schema == "flopbench-probe-v1":
            return ProbeReport.model_validate(data)
        if schema == "flopbench-validator-doctor-v1":
            return ValidatorDoctorReport.model_validate(data)
    except ValidationError as exc:
        raise ReportError("report.validation_error", "Report does not satisfy its schema") from exc
    raise ReportError("report.unsupported_schema", "Report schema is not supported")


def load_export(path: Path, *, max_bytes: int = MAX_REPORT_BYTES) -> ReportExport:
    """Load and verify a previously exported report envelope."""

    try:
        if path.is_symlink() or not path.is_file():
            raise ReportError("report.unsafe_input", "Report input must be a regular file")
        if path.stat().st_size > max_bytes:
            raise ReportError("report.too_large", "Report exceeds the size limit")
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except ReportError:
        raise
    except OSError as exc:
        raise ReportError("report.read_error", "Report could not be read") from exc
    if len(raw) > max_bytes:
        raise ReportError("report.too_large", "Report exceeds the size limit")
    try:
        return ReportExport.model_validate(parse_json(raw))
    except ValidationError as exc:
        raise ReportError("report.validation_error", "Report export is invalid") from exc


def _profile_reference(profile: LoadedProfile) -> ProfileReference:
    return ProfileReference(
        id=profile.profile.id,
        sha256=profile.sha256,
        source_status=profile.profile.source_status,
    )


def create_export(
    payload: ReportPayload,
    privacy: PrivacyLevel,
    *,
    profile: LoadedProfile | None = None,
) -> ReportExport:
    """Redact a source report and bind its canonical provenance."""

    redacted = redact_report(payload, privacy)
    source_data = payload.model_dump(mode="json", by_alias=True)
    binding: Literal["source-report", "user-selected", "none"]
    if isinstance(payload, ReadinessReport):
        comparison_profile = payload.profile
        binding = "source-report"
    elif profile is not None:
        comparison_profile = _profile_reference(profile)
        binding = "user-selected"
    else:
        comparison_profile = None
        binding = "none"
    document = ReportDocument(
        schema="flopbench-report-document-v1",
        privacy_level=privacy,
        payload=redacted,
        comparison_profile=comparison_profile,
        provenance=ReportProvenance(
            exporter_version=__version__,
            source_tool_version=payload.tool_version,
            source_jcs_sha256=(
                canonical_digest(source_data) if privacy is PrivacyLevel.PRIVATE else None
            ),
            profile_binding=binding,
        ),
    )
    digest = canonical_digest(document.model_dump(mode="json", by_alias=True))
    return ReportExport(
        schema="flopbench-report-export-v1",
        document=document,
        digest=ReportDigest(value=digest),
    )


def write_new_file(path: Path, content: bytes) -> None:
    """Write a complete export without following or replacing an existing path."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(content)
            handle.flush()
    except FileExistsError as exc:
        raise ReportError("report.output_exists", "Output already exists") from exc
    except OSError as exc:
        try:
            if path.is_file() and not path.is_symlink():
                path.unlink()
        except OSError:
            pass
        raise ReportError("report.write_error", "Report output could not be written") from exc
