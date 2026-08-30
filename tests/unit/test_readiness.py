from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from flopbench.contracts import (
    PrivacyLevel,
    ReadinessReport,
    ResultStatus,
    Role,
)
from flopbench.probe.models import CpuInfo, DiskKind
from flopbench.probe.service import run_fixture_probe
from flopbench.profile_loader import load_profile
from flopbench.readiness.engine import evaluate_readiness

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "fixtures" / "hardware"
PROFILE = load_profile(ROOT / "profiles" / "flop-teaser-0.1.yaml")


def _evaluate(fixture: str, role: Role = Role.MINER) -> ReadinessReport:
    probe = run_fixture_probe(HARDWARE / fixture, PrivacyLevel.PRIVATE)
    return evaluate_readiness(probe, PROFILE, role)


def test_no_supported_gpu_is_a_failure_with_reason() -> None:
    report = _evaluate("cpu-only.json")

    assert report.checks[0].status is ResultStatus.FAIL
    assert report.checks[0].reason_codes == ["miner.no_supported_gpu"]


def test_unsupported_provider_is_not_hardware_failure() -> None:
    report = _evaluate("unsupported-gpu.json")

    assert report.checks[0].status is ResultStatus.UNSUPPORTED
    assert report.summary.unsupported == 2
    assert report.summary.fail == 0


def test_community_headroom_passes_for_24_gib_and_warns_at_16_gib() -> None:
    high = _evaluate("windows-nvidia-24gb.json")
    boundary = _evaluate("linux-nvidia-16gb.json")

    assert high.checks[1].status is ResultStatus.PASS
    assert boundary.checks[1].status is ResultStatus.WARN


def test_validator_unknown_physical_cores_and_missing_disks_are_unknown() -> None:
    probe = run_fixture_probe(HARDWARE / "linux-nvidia-16gb.json", PrivacyLevel.PRIVATE)
    changed = probe.model_copy(
        update={
            "cpu": CpuInfo(logical_cores=probe.cpu.logical_cores, physical_cores=None),
            "disks": [],
        }
    )
    report = evaluate_readiness(changed, PROFILE, Role.VALIDATOR)

    assert report.checks[0].status is ResultStatus.UNKNOWN
    assert report.checks[2].status is ResultStatus.UNKNOWN
    assert report.checks[3].status is ResultStatus.UNKNOWN


def test_validator_known_non_nvme_disk_fails_type_check() -> None:
    probe = run_fixture_probe(HARDWARE / "linux-amd-16gb.json", PrivacyLevel.PRIVATE)
    assert probe.disks[0].kind is DiskKind.SSD

    report = evaluate_readiness(probe, PROFILE, Role.VALIDATOR)

    assert (
        next(c for c in report.checks if c.code == "validator.disk_kind").status
        is ResultStatus.FAIL
    )


def test_report_rejects_summary_counters_that_do_not_match_statuses() -> None:
    report = _evaluate("windows-nvidia-24gb.json")
    payload = report.model_dump(mode="json", by_alias=True)
    payload["summary"]["pass"] = 0
    payload["summary"]["fail"] = len(report.checks)

    with pytest.raises(ValidationError, match="summary counters must match"):
        ReadinessReport.model_validate(payload)


def test_every_readiness_decision_has_a_machine_reason_code() -> None:
    reports = [
        _evaluate("windows-nvidia-24gb.json"),
        _evaluate("missing-driver.json"),
        _evaluate("unsupported-gpu.json"),
        _evaluate("linux-nvidia-16gb.json", Role.VALIDATOR),
    ]

    assert all(check.reason_codes for report in reports for check in report.checks)
    assert all(
        " " not in code
        for report in reports
        for check in report.checks
        for code in check.reason_codes
    )
