"""Machine and human-readable Stage 3 readiness output."""

from __future__ import annotations

import json

from flopbench.contracts import ReadinessCheck, ReadinessReport


def readiness_json(report: ReadinessReport) -> str:
    payload = report.model_dump(mode="json", by_alias=True, exclude_none=True)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _line(check: ReadinessCheck) -> str:
    actual = "unknown" if check.actual is None else str(check.actual)
    threshold = "none" if check.threshold is None else str(check.threshold)
    return (
        f"- {check.code}: {check.status.value.upper()} "
        f"(actual={actual}, threshold={threshold}, reason={check.reason_codes[0]})"
    )


def readiness_terminal(report: ReadinessReport) -> str:
    source_checks = [check for check in report.checks if check.source_kind == "source_profile"]
    community_checks = [check for check in report.checks if check.source_kind == "community"]
    lines = [
        f"FlopBench {report.role.value} readiness",
        (
            f"Profile: {report.profile.id} "
            f"({report.profile.source_status.value}, sha256={report.profile.sha256})"
        ),
        "Source profile checks:",
        *(_line(check) for check in source_checks),
    ]
    if community_checks:
        lines.extend(["FlopBench community health checks:", *(_line(c) for c in community_checks)])
    lines.append(
        "Summary: "
        f"pass={report.summary.pass_} warn={report.summary.warn} "
        f"fail={report.summary.fail} unknown={report.summary.unknown} "
        f"skipped={report.summary.skipped} unsupported={report.summary.unsupported}"
    )
    return "\n".join(lines)
