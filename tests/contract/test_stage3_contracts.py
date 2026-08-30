from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.contracts import PrivacyLevel, ReadinessCheck, ReadinessReport, ResultStatus, Role
from flopbench.probe.service import run_fixture_probe
from flopbench.profile_loader import load_profile
from flopbench.readiness.engine import evaluate_readiness
from flopbench.readiness.formatters import readiness_json, readiness_terminal

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "fixtures" / "hardware"
PROFILE_PATH = ROOT / "profiles" / "flop-teaser-0.1.yaml"

pytestmark = pytest.mark.stage3


def _report(fixture: str, role: Role = Role.MINER) -> ReadinessReport:
    probe = run_fixture_probe(HARDWARE / fixture, PrivacyLevel.PUBLIC)
    return evaluate_readiness(probe, load_profile(PROFILE_PATH), role)


def _check(fixture: str, code: str, role: Role = Role.MINER) -> ReadinessCheck:
    report = _report(fixture, role)
    return next(check for check in report.checks if check.code == code)


@pytest.mark.parametrize(
    "fixture",
    ["windows-nvidia-24gb.json", "linux-nvidia-16gb.json"],
)
def test_s3_t01_t02_vram_at_or_above_threshold_passes(fixture: str) -> None:
    check = _check(fixture, "miner.vram_bytes")

    assert check.status is ResultStatus.PASS
    assert isinstance(check.actual, int)
    assert isinstance(check.threshold, int)
    assert check.actual >= check.threshold


def test_s3_t03_vram_is_not_rounded_up() -> None:
    check = _check("miner-vram-15-99gb.json", "miner.vram_bytes")

    assert check.actual == 17_169_131_765
    assert check.threshold == 16 * 1024**3
    assert check.status is ResultStatus.FAIL


def test_s3_t04_unknown_vram_is_not_automatic_failure() -> None:
    check = _check("missing-driver.json", "miner.vram_bytes")

    assert check.status is ResultStatus.UNKNOWN
    assert check.actual is None


def test_s3_t05_validator_boundary_fixture_passes_source_capacity_checks() -> None:
    report = _report("linux-nvidia-16gb.json", Role.VALIDATOR)
    source_checks = [check for check in report.checks if check.source_kind == "source_profile"]

    assert [check.status for check in source_checks[:4]] == [ResultStatus.PASS] * 4
    assert source_checks[4].status is ResultStatus.SKIPPED


def test_s3_t06_only_memory_source_check_fails() -> None:
    report = _report("low-memory-validator.json", Role.VALIDATOR)
    failed = [check.code for check in report.checks if check.status is ResultStatus.FAIL]

    assert failed == ["validator.memory_bytes"]


def test_s3_t07_unknown_disk_kind_stays_unknown() -> None:
    report = _report("validator-unknown-disk-kind.json", Role.VALIDATOR)

    assert (
        next(c for c in report.checks if c.code == "validator.disk_capacity_bytes").status
        is ResultStatus.PASS
    )
    assert (
        next(c for c in report.checks if c.code == "validator.disk_kind").status
        is ResultStatus.UNKNOWN
    )


def test_s3_t08_draft_status_is_visible_in_json_and_terminal() -> None:
    report = _report("linux-nvidia-16gb.json")

    assert json.loads(readiness_json(report))["profile"]["source_status"] == "draft"
    assert "(draft," in readiness_terminal(report)


def test_s3_t09_community_check_is_never_labeled_as_source_profile() -> None:
    report = _report("linux-nvidia-16gb.json")
    community = next(c for c in report.checks if c.code == "community.miner.vram_headroom")
    source = next(c for c in report.checks if c.code == "miner.vram_bytes")

    assert community.source_kind == "community"
    assert source.source_kind == "source_profile"
    assert community.required is False
    assert community.reason_codes[0].startswith("community.")


def test_cli_json_is_deterministic_and_contains_all_summary_states() -> None:
    args = [
        "check",
        "miner",
        "--fixture",
        str(HARDWARE / "linux-nvidia-16gb.json"),
        "--profile",
        str(PROFILE_PATH),
        "--format",
        "json",
    ]
    first = CliRunner().invoke(app, args)
    second = CliRunner().invoke(app, args)

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout
    assert set(json.loads(first.stdout)["summary"]) == {
        "pass",
        "warn",
        "fail",
        "unknown",
        "skipped",
        "unsupported",
    }


def test_cli_terminal_is_clear_and_avoids_prohibited_score_language() -> None:
    result = CliRunner().invoke(
        app,
        [
            "check",
            "validator",
            "--fixture",
            str(HARDWARE / "linux-nvidia-16gb.json"),
            "--profile",
            str(PROFILE_PATH),
        ],
    )

    assert result.exit_code == 0
    assert "Source profile checks:" in result.stdout
    assert "reason=" in result.stdout
    lowered = result.stdout.lower()
    assert all(term not in lowered for term in ("eligible", "airdrop score", "official score"))
