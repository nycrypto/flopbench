"""Stage 11 stable-release and end-to-end publication acceptance tests."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scripts.check_links import broken_links
from scripts.generate_examples import DEFAULT_OUTPUT, example_files
from scripts.verify_release_tag import verify

from flopbench import __version__
from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import PrivacyLevel, ReadinessReport, Receipt, Role
from flopbench.receipt.codec import encode_base64url, encode_ed25519_did
from flopbench.receipt.service import (
    create_receipt,
    prepare_receipt,
    signing_bytes,
    verify_receipt,
)
from flopbench.reporting.models import ReportExport
from flopbench.reporting.service import create_export, load_report
from flopbench.simulator.models import SessionState, SimulationResult

pytestmark = pytest.mark.stage11
ROOT = Path(__file__).resolve().parents[2]
RFC8032_TEST_SEED = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
)


def _json(name: str) -> object:
    return json.loads((DEFAULT_OUTPUT / name).read_text(encoding="utf-8"))


def test_s11_t01_stable_version_and_release_tag_contract_match() -> None:
    assert __version__ == "1.0.0"
    assert verify(ROOT, "v1.0.0") == []
    assert verify(ROOT, "v1.0.0-rc.1")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "1.0.0"' in pyproject
    assert "Development Status :: 5 - Production/Stable" in pyproject


def test_s11_t02_public_miner_and_validator_examples_are_strict_reports() -> None:
    miner = ReadinessReport.model_validate(_json("miner-readiness.public.json"))
    validator = ReadinessReport.model_validate(_json("validator-readiness.public.json"))
    assert miner.role is Role.MINER
    assert validator.role is Role.VALIDATOR
    assert miner.environment.privacy_level is PrivacyLevel.PUBLIC
    assert validator.environment.privacy_level is PrivacyLevel.PUBLIC
    assert miner.profile.source_status.value == "draft"
    assert validator.summary.skipped == 1
    assert {check.status.value for check in miner.checks} <= {
        "pass",
        "warn",
        "fail",
        "unknown",
        "skipped",
        "unsupported",
    }


def test_s11_t03_mock_benchmark_is_deterministic_and_complete() -> None:
    report = BenchmarkReportV2.model_validate(_json("mock-benchmark.json"))
    assert report.adapter.name == "mock"
    assert report.metrics.ttft.confidence.value == "simulated"
    assert report.outcomes.success == report.workload.measured_runs
    assert report.outcomes.error_rate == 0
    assert (DEFAULT_OUTPUT / "mock-benchmark.json").read_bytes() == example_files()[
        "mock-benchmark.json"
    ]


def test_s11_t04_public_preview_contains_no_private_fixture_fields() -> None:
    raw = (DEFAULT_OUTPUT / "public-readiness-report.json").read_bytes()
    exported = ReportExport.model_validate_json(raw)
    assert exported.document.privacy_level is PrivacyLevel.PUBLIC
    assert exported.document.provenance.source_jcs_sha256 is None
    lowered = raw.lower()
    for secret in (
        b"hostname",
        b"user_name",
        b"mount_point",
        b"serial_number",
        b"pci_bus_id",
        b"access_token",
        b"private_key",
    ):
        assert secret not in lowered


def test_s11_t05_offline_html_has_no_script_or_network_dependency() -> None:
    html = (DEFAULT_OUTPUT / "public-readiness-report.html").read_bytes()
    lowered = html.lower()
    assert lowered.startswith(b"<!doctype html>")
    assert b"content-security-policy" in lowered
    assert b"<script" not in lowered
    assert b"src=" not in lowered
    assert b"href=" not in lowered
    assert b"http://" not in lowered
    assert b"https://" not in lowered


def test_s11_t06_prepare_create_and_verify_receipt_round_trip() -> None:
    # This is the public RFC 8032 test seed, never user or maintainer key material.
    source = load_report(DEFAULT_OUTPUT / "miner-readiness.public.json")
    exported = create_export(source, PrivacyLevel.PUBLIC)
    test_key = Ed25519PrivateKey.from_private_bytes(RFC8032_TEST_SEED)
    did = encode_ed25519_did(test_key.public_key().public_bytes_raw())
    request = prepare_receipt(exported, did, datetime(2026, 1, 1, tzinfo=UTC))
    signature = encode_base64url(test_key.sign(signing_bytes(request.payload)))
    receipt: Receipt = create_receipt(request, signature)
    result = verify_receipt(exported, receipt)
    assert result.valid is True
    assert result.proof == "ed25519-key-possession"
    assert result.authenticity == "report-claims-not-independently-verified"


def test_s11_t07_agent_normal_and_challenge_examples_reach_expected_states() -> None:
    normal = SimulationResult.model_validate(_json("agent-simulation.json"))
    challenge = SimulationResult.model_validate(_json("agent-validator-challenge.json"))
    assert normal.final_state is SessionState.SETTLED
    assert normal.challenge is None
    assert challenge.final_state is SessionState.REJECTED
    assert challenge.challenge is not None
    assert challenge.challenge.reason_code == "validator_sample_mismatch"
    assert normal.official_protocol is False
    assert challenge.accounting.mock_slashed.unit == "mock-credit"


def test_s11_t08_clean_uninstall_gate_preserves_user_reports() -> None:
    verifier = (ROOT / "scripts" / "verify_install.py").read_text(encoding="utf-8")
    assert "before =" in verifier
    assert "after =" in verifier
    assert "Uninstall changed user-owned reports" in verifier
    noxfile = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    assert "def install_candidate(session: nox.Session)" in noxfile
    assert '"scripts/verify_install.py"' in noxfile


def test_s11_t09_ci_repeats_quality_install_and_e2e_on_windows_and_ubuntu() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "python -m nox -s unit contract security" in workflow
    assert "python -m nox -s docs" in workflow
    assert "python -m nox -s install" in workflow
    assert "@flopbench/web e2e" in workflow


def test_stage11_examples_are_byte_stable_and_complete() -> None:
    expected = example_files()
    assert {path.name for path in DEFAULT_OUTPUT.iterdir()} == set(expected)
    for name, content in expected.items():
        assert (DEFAULT_OUTPUT / name).read_bytes() == content


def test_stage11_demo_is_real_webm_and_fixture_only_documented() -> None:
    video = ROOT / "docs" / "assets" / "flopbench-dashboard-demo.webm"
    assert video.stat().st_size > 100_000
    assert video.read_bytes()[:4] == bytes.fromhex("1a45dfa3")
    documentation = (ROOT / "docs" / "demo.md").read_text(encoding="utf-8").lower()
    assert "deterministic fixtures" in documentation
    assert "local-only" in documentation


def test_stage11_release_workflow_is_tag_only_pinned_and_fail_closed() -> None:
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    assert yaml.safe_load(workflow) is not None
    uses = re.findall(r"^\s*uses:\s*([^\s]+)", workflow, flags=re.MULTILINE)
    assert uses
    assert all(re.search(r"@[0-9a-f]{40}$", reference) for reference in uses)
    assert '      - "v1.0.0"' in workflow
    assert "id-token: write" in workflow
    assert "attestations: write" in workflow
    assert "pull-requests: write" not in workflow
    assert "fetch-depth: 0" in workflow
    assert 'git merge-base --is-ancestor "$GITHUB_SHA" "origin/main"' in workflow
    assert workflow.index("Create draft release") < workflow.index("Attest release artifacts")
    assert workflow.index("Attest release artifacts") < workflow.index("Publish attested release")


def test_stage11_publication_documents_keep_unofficial_boundaries() -> None:
    paths = [
        ROOT / "README.md",
        ROOT / "README.tr.md",
        ROOT / "ROADMAP.md",
        ROOT / "docs" / "releases" / "v1.0.0.md",
        ROOT / "docs" / "limitations.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    assert "not an official" in combined
    assert "resmî" in combined
    assert "eligibility" in combined
    assert "stage 12" in combined
    assert "blocked" in combined
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.yml").is_file()
    assert (ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.yml").is_file()


def test_stage11_markdown_link_checker_rejects_missing_target(tmp_path: Path) -> None:
    document = tmp_path / "README.md"
    document.write_text("[missing](./no-such-file.md)\n", encoding="utf-8")
    assert broken_links(tmp_path) == ["README.md:1: missing target ./no-such-file.md"]
    assert broken_links(ROOT) == []
