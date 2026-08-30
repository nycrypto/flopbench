"""Stage 2 public-output privacy boundary."""

from __future__ import annotations

from flopbench.contracts import PrivacyLevel
from flopbench.probe.models import ProbeReport


def public_report(report: ProbeReport) -> ProbeReport:
    """Remove host, path, serial, and bus identifiers for public output."""

    system = report.system.model_copy(update={"os_version": None, "host": None})
    disks = [disk.model_copy(update={"device": None, "mount_point": None}) for disk in report.disks]
    devices = [
        device.model_copy(update={"pci_bus_id": None, "serial_number": None})
        for device in report.gpu.devices
    ]
    gpu = report.gpu.model_copy(update={"devices": devices})
    return report.model_copy(
        update={
            "privacy_level": PrivacyLevel.PUBLIC,
            "system": system,
            "disks": disks,
            "gpu": gpu,
        }
    )
