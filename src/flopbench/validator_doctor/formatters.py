"""Deterministic JSON and clear terminal output for validator doctor."""

from __future__ import annotations

import json

from flopbench.validator_doctor.models import ValidatorDoctorReport


def doctor_json(report: ValidatorDoctorReport) -> str:
    payload = report.model_dump(mode="json", by_alias=True)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def doctor_terminal(report: ValidatorDoctorReport) -> str:
    return "\n".join(
        [
            "FlopBench validator active health tests",
            f"Disk: {report.disk.status.value.upper()} ({report.disk.reason_codes[0]})",
            (
                f"Network: {report.network.status.value.upper()} "
                f"target={report.network.target or 'not-selected'} "
                f"({report.network.reason_codes[0]})"
            ),
            (
                f"Clock: {report.clock.status.value.upper()} "
                f"server={report.clock.server or 'not-selected'} "
                f"({report.clock.reason_codes[0]})"
            ),
        ]
    )
