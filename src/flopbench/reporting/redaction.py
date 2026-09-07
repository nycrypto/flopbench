"""Explicit disclosure profiles for exported reports."""

from __future__ import annotations

import re

from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import BenchmarkReport, PrivacyLevel, ReadinessReport
from flopbench.probe.models import ProbeReport
from flopbench.validator_doctor.models import ValidatorDoctorReport

from .models import ReportPayload

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|authorization|bearer)\b", re.IGNORECASE),
    re.compile(r"\btoken[-_:= ]+secret\b", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:wallet[_ -]?seed|seed[_ -]?phrase|mnemonic)\b", re.IGNORECASE),
)


def contains_secret_marker(value: object) -> bool:
    """Detect credential material in every string-bearing branch."""

    if isinstance(value, str):
        return any(pattern.search(value) for pattern in _SECRET_PATTERNS)
    if isinstance(value, dict):
        return any(
            contains_secret_marker(key) or contains_secret_marker(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(contains_secret_marker(item) for item in value)
    return False


def redact_report(payload: ReportPayload, privacy: PrivacyLevel) -> ReportPayload:
    """Return a typed report at the requested disclosure level."""

    if isinstance(payload, ProbeReport):
        if privacy is PrivacyLevel.PRIVATE:
            redacted: ReportPayload = payload.model_copy(update={"privacy_level": privacy})
        else:
            system_update: dict[str, object] = {"host": None}
            if privacy is PrivacyLevel.PUBLIC:
                system_update["os_version"] = None
            system = payload.system.model_copy(update=system_update)
            disks = [
                disk.model_copy(update={"device": None, "mount_point": None})
                for disk in payload.disks
            ]
            devices = [
                device.model_copy(update={"pci_bus_id": None, "serial_number": None})
                for device in payload.gpu.devices
            ]
            redacted = payload.model_copy(
                update={
                    "privacy_level": privacy,
                    "system": system,
                    "disks": disks,
                    "gpu": payload.gpu.model_copy(update={"devices": devices}),
                }
            )
    elif isinstance(payload, ReadinessReport):
        environment = payload.environment.model_copy(update={"privacy_level": privacy})
        redacted = payload.model_copy(update={"environment": environment})
    elif isinstance(payload, ValidatorDoctorReport) and privacy is not PrivacyLevel.PRIVATE:
        redacted = payload.model_copy(
            update={
                "network": payload.network.model_copy(update={"target": None}),
                "clock": payload.clock.model_copy(update={"server": None}),
            }
        )
    elif isinstance(payload, (BenchmarkReport, BenchmarkReportV2, ValidatorDoctorReport)):
        redacted = payload
    else:
        raise TypeError("unsupported report type")
    if contains_secret_marker(redacted.model_dump(mode="json", by_alias=True)):
        raise ValueError("report contains credential-like material")
    return redacted
