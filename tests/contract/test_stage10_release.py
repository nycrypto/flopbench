"""Stage 10 release-candidate and compatibility acceptance tests."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from time import perf_counter

import pytest
from typer.testing import CliRunner

import flopbench.release as release_module
from flopbench import __version__
from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.cli import app as cli_app
from flopbench.config import ConfigError, LocalConfig, load_config
from flopbench.contracts import BenchmarkReport, PrivacyLevel
from flopbench.probe.service import run_fixture_probe
from flopbench.profile_loader import load_profile
from flopbench.release import (
    ReleaseError,
    finalize,
    license_report,
    locked_dependencies,
    sha256_file,
    validate_cyclonedx,
    verify_checksums,
    write_checksums,
)
from flopbench.release import (
    main as release_main,
)
from flopbench.reporting.render import render_json
from flopbench.reporting.service import create_export, load_report
from flopbench.simulator import SimulationScenario, build_session_request, run_simulation

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_LOCK = ROOT / "requirements" / "runtime.txt"
LICENSE_POLICY = ROOT / "release" / "license-policy.json"
pytestmark = pytest.mark.stage10


def sbom_payload(*, include_dependencies: bool = True) -> dict[str, object]:
    components = (
        [
            {"name": dependency.normalized_name, "version": dependency.version}
            for dependency in locked_dependencies(RUNTIME_LOCK)
        ]
        if include_dependencies
        else []
    )
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "components": components}


def test_s10_t04_missing_config_is_private_and_malformed_config_is_explicit(
    tmp_path: Path,
) -> None:
    default = load_config(tmp_path / "missing.json")
    assert default == LocalConfig()
    assert default.default_privacy is PrivacyLevel.PRIVATE

    malformed = tmp_path / "config.json"
    malformed.write_text('{"schema":"flopbench-config-v1","remote_bind":true}', encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid") as captured:
        load_config(malformed)
    assert captured.value.code == "config.invalid"

    cli = CliRunner().invoke(cli_app, ["serve", "--config", str(malformed)])
    assert cli.exit_code == 2
    assert "config.invalid" in cli.output


def test_s10_t04_unsafe_and_oversized_configs_fail_closed(tmp_path: Path) -> None:
    directory = tmp_path / "config-directory"
    directory.mkdir()
    with pytest.raises(ConfigError) as directory_error:
        load_config(directory)
    assert directory_error.value.code == "config.unsafe_input"

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b" " * (64 * 1024 + 1))
    with pytest.raises(ConfigError) as size_error:
        load_config(oversized)
    assert size_error.value.code == "config.too_large"

    invalid_utf8 = tmp_path / "invalid-utf8.json"
    invalid_utf8.write_bytes(b"\xff")
    with pytest.raises(ConfigError) as encoding_error:
        load_config(invalid_utf8)
    assert encoding_error.value.code == "config.invalid"


def test_s10_t04_config_symlink_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "real.json"
    target.write_text("{}", encoding="utf-8")
    link = tmp_path / "config.json"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("This platform does not permit test symlinks")
    with pytest.raises(ConfigError) as captured:
        load_config(link)
    assert captured.value.code == "config.unsafe_input"


def test_s10_t04_config_none_valid_file_and_read_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert load_config().default_privacy is PrivacyLevel.PRIVATE
    valid = tmp_path / "valid.json"
    valid.write_text(
        '{"schema":"flopbench-config-v1","default_privacy":"public","dashboard_theme":"light"}',
        encoding="utf-8",
    )
    loaded = load_config(valid)
    assert loaded.default_privacy is PrivacyLevel.PUBLIC
    assert loaded.dashboard_theme == "light"

    original = Path.read_bytes

    def fail_read(path: Path) -> bytes:
        if path == valid:
            raise OSError("synthetic read failure")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", fail_read)
    with pytest.raises(ConfigError) as captured:
        load_config(valid)
    assert captured.value.code == "config.read_error"


def test_s10_t04_symlink_check_fails_before_missing_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "broken-link.json"
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == missing or original(path))
    with pytest.raises(ConfigError) as captured:
        load_config(missing)
    assert captured.value.code == "config.unsafe_input"


def test_s10_t05_old_v1_report_opens_without_mutation() -> None:
    path = ROOT / "fixtures" / "reports" / "benchmark-valid.json"
    original = path.read_bytes()

    report = load_report(path)

    assert isinstance(report, BenchmarkReport)
    assert not isinstance(report, BenchmarkReportV2)
    assert report.schema_id == "flopbench-benchmark-report-v1"
    assert path.read_bytes() == original


def test_s10_t06_release_tools_and_runtime_dependencies_are_exactly_locked() -> None:
    release_lock = (ROOT / "requirements" / "release.txt").read_text(encoding="utf-8")
    assert "pip-audit==2.10.1" in release_lock
    assert "detect-secrets==1.5.0" in release_lock
    assert len(locked_dependencies(RUNTIME_LOCK)) == 27
    dependencies = license_report(RUNTIME_LOCK, LICENSE_POLICY)["dependencies"]
    assert isinstance(dependencies, list)
    assert len(dependencies) == 27


def test_s10_t07_reviewed_secret_baseline_exists() -> None:
    baseline = json.loads((ROOT / ".secrets.baseline").read_text(encoding="utf-8"))
    assert baseline["version"] == "1.5.0"
    assert isinstance(baseline["results"], dict)


def test_s10_t08_checksums_cover_artifacts_and_detect_tampering(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    wheel = artifact_dir / f"flopbench-{__version__}-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    (artifact_dir / f"flopbench-{__version__}.tar.gz").write_bytes(b"sdist")
    sbom = artifact_dir / f"flopbench-{__version__}.cdx.json"
    sbom.write_text(json.dumps(sbom_payload()), encoding="utf-8")

    finalize(artifact_dir, RUNTIME_LOCK, LICENSE_POLICY, sbom)
    verify_checksums(artifact_dir)
    wheel.write_bytes(b"tampered")

    with pytest.raises(ReleaseError, match="Checksum mismatch"):
        verify_checksums(artifact_dir)


def test_s10_t08_checksum_manifest_rejects_extra_and_malformed_files(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    artifact = artifact_dir / f"flopbench-{__version__}.whl"
    artifact.write_bytes(b"wheel")
    checksum = write_checksums(artifact_dir)

    (artifact_dir / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ReleaseError, match="exact artifact set"):
        verify_checksums(artifact_dir)
    (artifact_dir / "extra.txt").unlink()

    checksum.write_text("not-a-checksum\n", encoding="ascii")
    with pytest.raises(ReleaseError, match="malformed"):
        verify_checksums(artifact_dir)


def test_s10_t08_release_metadata_must_cover_lock_exactly(tmp_path: Path) -> None:
    invalid_sbom = tmp_path / "invalid-sbom.json"
    invalid_sbom.write_text('{"bomFormat":"Other"}', encoding="utf-8")
    with pytest.raises(ReleaseError, match="not CycloneDX"):
        validate_cyclonedx(invalid_sbom, RUNTIME_LOCK)

    missing_sbom = tmp_path / "missing-sbom.json"
    missing_sbom.write_text(
        '{"bomFormat":"CycloneDX","specVersion":"1.6","components":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ReleaseError, match="missing or mismatched runtime components"):
        validate_cyclonedx(missing_sbom, RUNTIME_LOCK)

    vulnerable_sbom = tmp_path / "vulnerable-sbom.json"
    vulnerable = sbom_payload()
    vulnerable["vulnerabilities"] = [{"id": "SYNTHETIC-TEST"}]
    vulnerable_sbom.write_text(json.dumps(vulnerable), encoding="utf-8")
    with pytest.raises(ReleaseError, match="known vulnerabilities"):
        validate_cyclonedx(vulnerable_sbom, RUNTIME_LOCK)

    mismatched_sbom = tmp_path / "mismatched-sbom.json"
    mismatched = sbom_payload()
    assert isinstance(mismatched["components"], list)
    mismatched["components"][0]["version"] = "0.0.0"
    mismatched_sbom.write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(ReleaseError, match="missing or mismatched"):
        validate_cyclonedx(mismatched_sbom, RUNTIME_LOCK)

    incomplete_policy = tmp_path / "license-policy.json"
    incomplete_policy.write_text(
        '{"schema":"flopbench-license-policy-v1","packages":{}}',
        encoding="utf-8",
    )
    with pytest.raises(ReleaseError, match="License policy mismatch"):
        license_report(RUNTIME_LOCK, incomplete_policy)

    wrong_policy = tmp_path / "wrong-policy.json"
    wrong_policy.write_text('{"schema":"other","packages":{}}', encoding="utf-8")
    with pytest.raises(ReleaseError, match="Unsupported license"):
        license_report(RUNTIME_LOCK, wrong_policy)

    malformed_policy = tmp_path / "malformed-policy.json"
    malformed_policy.write_text(
        '{"schema":"flopbench-license-policy-v1","packages":[]}',
        encoding="utf-8",
    )
    with pytest.raises(ReleaseError, match="must map"):
        license_report(RUNTIME_LOCK, malformed_policy)


def test_s10_t08_release_inputs_reject_unsafe_shapes(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ReleaseError, match="no artifacts"):
        write_checksums(empty)

    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    (artifact_dir / "nested").mkdir()
    with pytest.raises(ReleaseError, match="Not a regular file"):
        write_checksums(artifact_dir)

    lock = tmp_path / "empty-lock.txt"
    lock.write_text("# no packages\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="no exact dependency"):
        locked_dependencies(lock)

    duplicate_lock = tmp_path / "duplicate-lock.txt"
    duplicate_lock.write_text("demo==1\ndemo==1\n", encoding="utf-8")
    with pytest.raises(ReleaseError, match="Duplicate"):
        locked_dependencies(duplicate_lock)


def test_s10_t08_invalid_text_and_json_metadata_are_controlled(tmp_path: Path) -> None:
    invalid_lock = tmp_path / "invalid-lock.txt"
    invalid_lock.write_bytes(b"\xff")
    with pytest.raises(ReleaseError, match="Invalid runtime lock"):
        locked_dependencies(invalid_lock)

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ReleaseError, match="Invalid JSON"):
        validate_cyclonedx(invalid_json, RUNTIME_LOCK)

    array_json = tmp_path / "array.json"
    array_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ReleaseError, match="must be an object"):
        validate_cyclonedx(array_json, RUNTIME_LOCK)

    no_components = tmp_path / "no-components.json"
    no_components.write_text('{"bomFormat":"CycloneDX","specVersion":"1.6"}', encoding="utf-8")
    with pytest.raises(ReleaseError, match="components are missing"):
        validate_cyclonedx(no_components, RUNTIME_LOCK)


def test_s10_t08_checksum_rejects_duplicates_non_ascii_and_unsafe_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    artifact = artifact_dir / "artifact.whl"
    artifact.write_bytes(b"wheel")
    digest = sha256_file(artifact)
    checksum = artifact_dir / "SHA256SUMS"
    checksum.write_text(f"{digest}  artifact.whl\n{digest}  artifact.whl\n", encoding="ascii")
    with pytest.raises(ReleaseError, match="duplicates"):
        verify_checksums(artifact_dir)

    checksum.write_bytes(b"\xff")
    with pytest.raises(ReleaseError, match="valid ASCII"):
        verify_checksums(artifact_dir)

    checksum.write_text(f"{digest}  artifact.whl\n", encoding="ascii")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == artifact or original(path))
    with pytest.raises(ReleaseError, match="Not a regular file"):
        verify_checksums(artifact_dir)


def test_s10_t08_size_limits_and_finalize_shape_are_enforced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact = tmp_path / "artifact.whl"
    artifact.write_bytes(b"x")
    monkeypatch.setattr(release_module, "MAX_ARTIFACT_BYTES", 0)
    with pytest.raises(ReleaseError, match="size limit"):
        sha256_file(artifact)

    missing = tmp_path / "missing"
    with pytest.raises(ReleaseError, match="regular directory"):
        finalize(missing, RUNTIME_LOCK, LICENSE_POLICY, missing / "sbom.json")
    with pytest.raises(ReleaseError, match="regular directory"):
        verify_checksums(missing)

    linked_directory = tmp_path / "linked-release"
    linked_directory.mkdir()
    original_is_symlink = Path.is_symlink
    with monkeypatch.context() as link_patch:
        link_patch.setattr(
            Path,
            "is_symlink",
            lambda path: path == linked_directory or original_is_symlink(path),
        )
        with pytest.raises(ReleaseError, match="regular directory"):
            verify_checksums(linked_directory)

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    with pytest.raises(ReleaseError, match="exactly one wheel"):
        finalize(incomplete, RUNTIME_LOCK, LICENSE_POLICY, incomplete / "sbom.json")


def test_s10_t08_release_cli_finalizes_verifies_and_reports_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    artifact_dir = tmp_path / "release"
    artifact_dir.mkdir()
    (artifact_dir / f"flopbench-{__version__}-py3-none-any.whl").write_bytes(b"wheel")
    (artifact_dir / f"flopbench-{__version__}.tar.gz").write_bytes(b"sdist")
    sbom = artifact_dir / f"flopbench-{__version__}.cdx.json"
    sbom.write_text(json.dumps(sbom_payload()), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "flopbench.release",
            "finalize",
            "--artifact-dir",
            str(artifact_dir),
            "--runtime-lock",
            str(RUNTIME_LOCK),
            "--license-policy",
            str(LICENSE_POLICY),
            "--sbom",
            str(sbom),
        ],
    )
    release_main()

    monkeypatch.setattr(
        sys,
        "argv",
        ["flopbench.release", "verify", "--artifact-dir", str(artifact_dir)],
    )
    release_main()

    (artifact_dir / f"flopbench-{__version__}.tar.gz").write_bytes(b"tampered")
    with pytest.raises(SystemExit, match="2"):
        release_main()


def test_s10_t09_offline_probe_and_report_never_open_a_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def deny_network(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("offline path attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    report = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "cpu-only.json",
        PrivacyLevel.PRIVATE,
    )
    export = create_export(
        report,
        PrivacyLevel.PUBLIC,
        profile=load_profile(ROOT / "profiles" / "flop-teaser-0.1.yaml"),
    )

    assert b"flopbench-report-export-v1" in render_json(export)


def test_stage10_performance_regression_budget() -> None:
    started = perf_counter()
    for seed in range(500):
        request = build_session_request(SimulationScenario.SUCCESS, seed=seed)
        result = run_simulation(request)
        assert result.final_state.value == "settled"
    assert perf_counter() - started < 3.0
