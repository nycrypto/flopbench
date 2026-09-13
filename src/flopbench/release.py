"""Release artifact integrity and license-policy helpers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flopbench import __version__

LOCKED_REQUIREMENT = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.-]*)==([^\s\\]+)")
SHA256_LINE = re.compile(r"^([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.+\-]*)$")
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024


class ReleaseError(Exception):
    """Controlled release validation error."""


@dataclass(frozen=True, slots=True)
class LockedDependency:
    name: str
    version: str

    @property
    def normalized_name(self) -> str:
        return re.sub(r"[-_.]+", "-", self.name).lower()


def _regular_file(path: Path, *, max_bytes: int = MAX_METADATA_BYTES) -> None:
    if path.is_symlink() or not path.is_file():
        raise ReleaseError(f"Not a regular file: {path.name}")
    if path.stat().st_size > max_bytes:
        raise ReleaseError(f"File exceeds size limit: {path.name}")


def _regular_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise ReleaseError("Release artifact directory must be a regular directory")


def locked_dependencies(path: Path) -> list[LockedDependency]:
    """Read exact pins from a pip-compile lock without executing requirement text."""

    _regular_file(path)
    dependencies: dict[str, LockedDependency] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseError(f"Invalid runtime lock: {path.name}") from exc
    for line in lines:
        match = LOCKED_REQUIREMENT.match(line)
        if match is None:
            continue
        dependency = LockedDependency(match.group(1), match.group(2))
        normalized = dependency.normalized_name
        if normalized in dependencies:
            raise ReleaseError(f"Duplicate locked dependency: {normalized}")
        dependencies[normalized] = dependency
    if not dependencies:
        raise ReleaseError("Runtime lock contains no exact dependency pins")
    return [dependencies[name] for name in sorted(dependencies)]


def _load_json(path: Path) -> dict[str, Any]:
    _regular_file(path)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"Invalid JSON metadata: {path.name}") from exc
    if not isinstance(value, dict):
        raise ReleaseError(f"JSON metadata must be an object: {path.name}")
    return value


def license_report(lock_path: Path, policy_path: Path) -> dict[str, object]:
    """Build a deterministic report only when policy covers every runtime dependency."""

    dependencies = locked_dependencies(lock_path)
    policy = _load_json(policy_path)
    if policy.get("schema") != "flopbench-license-policy-v1":
        raise ReleaseError("Unsupported license policy schema")
    packages = policy.get("packages")
    if not isinstance(packages, dict) or not all(
        isinstance(name, str) and isinstance(expression, str)
        for name, expression in packages.items()
    ):
        raise ReleaseError("License policy packages must map names to SPDX expressions")
    normalized_policy = {
        re.sub(r"[-_.]+", "-", name).lower(): expression for name, expression in packages.items()
    }
    expected = {dependency.normalized_name for dependency in dependencies}
    if set(normalized_policy) != expected:
        missing = sorted(expected - set(normalized_policy))
        extra = sorted(set(normalized_policy) - expected)
        raise ReleaseError(f"License policy mismatch; missing={missing}, extra={extra}")
    return {
        "schema": "flopbench-license-report-v1",
        "project": {"name": "flopbench", "version": __version__, "license": "Apache-2.0"},
        "dependencies": [
            {
                "name": dependency.normalized_name,
                "version": dependency.version,
                "license": normalized_policy[dependency.normalized_name],
                "compatible": True,
            }
            for dependency in dependencies
        ],
    }


def validate_cyclonedx(path: Path, lock_path: Path) -> None:
    """Require a CycloneDX SBOM containing every locked runtime component."""

    sbom = _load_json(path)
    if sbom.get("bomFormat") != "CycloneDX" or not isinstance(sbom.get("specVersion"), str):
        raise ReleaseError("SBOM is not CycloneDX JSON")
    components = sbom.get("components")
    if not isinstance(components, list):
        raise ReleaseError("SBOM components are missing")
    component_versions = {
        re.sub(r"[-_.]+", "-", name).lower(): version
        for component in components
        if isinstance(component, dict)
        and isinstance((name := component.get("name")), str)
        and isinstance((version := component.get("version")), str)
    }
    expected = {
        dependency.normalized_name: dependency.version
        for dependency in locked_dependencies(lock_path)
    }
    mismatched = sorted(
        name for name, version in expected.items() if component_versions.get(name) != version
    )
    if mismatched:
        raise ReleaseError(f"SBOM has missing or mismatched runtime components: {mismatched}")
    vulnerabilities = sbom.get("vulnerabilities")
    if vulnerabilities not in (None, []):
        raise ReleaseError("SBOM contains known vulnerabilities")


def sha256_file(path: Path) -> str:
    """Hash a bounded-stream regular file."""

    _regular_file(path, max_bytes=MAX_ARTIFACT_BYTES)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_new(path: Path, value: dict[str, object]) -> None:
    content = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
        handle.write("\n")


def write_checksums(artifact_dir: Path) -> Path:
    """Write one sorted checksum manifest without accepting nested or unsafe files."""

    _regular_directory(artifact_dir)
    checksum_path = artifact_dir / "SHA256SUMS"
    files = sorted(path for path in artifact_dir.iterdir() if path.name != checksum_path.name)
    if not files:
        raise ReleaseError("Release directory contains no artifacts")
    lines = []
    for path in files:
        _regular_file(path, max_bytes=MAX_ARTIFACT_BYTES)
        lines.append(f"{sha256_file(path)}  {path.name}\n")
    with checksum_path.open("x", encoding="ascii", newline="\n") as handle:
        handle.writelines(lines)
    return checksum_path


def verify_checksums(artifact_dir: Path) -> None:
    """Verify every artifact and reject missing, extra, duplicate, or unsafe names."""

    _regular_directory(artifact_dir)
    checksum_path = artifact_dir / "SHA256SUMS"
    _regular_file(checksum_path)
    recorded: dict[str, str] = {}
    try:
        lines = checksum_path.read_text(encoding="ascii").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ReleaseError("Checksum manifest is not valid ASCII") from exc
    for line in lines:
        match = SHA256_LINE.fullmatch(line)
        if match is None or match.group(2) in recorded:
            raise ReleaseError("Checksum manifest is malformed or contains duplicates")
        recorded[match.group(2)] = match.group(1)
    artifact_paths = [path for path in artifact_dir.iterdir() if path.name != checksum_path.name]
    for path in artifact_paths:
        _regular_file(path, max_bytes=MAX_ARTIFACT_BYTES)
    actual = {path.name for path in artifact_paths}
    if set(recorded) != actual:
        raise ReleaseError("Checksum manifest does not cover the exact artifact set")
    for name, expected in recorded.items():
        if sha256_file(artifact_dir / name) != expected:
            raise ReleaseError(f"Checksum mismatch: {name}")


def finalize(artifact_dir: Path, lock_path: Path, policy_path: Path, sbom_path: Path) -> None:
    """Validate RC inputs, emit license evidence, and bind every file by SHA-256."""

    _regular_directory(artifact_dir)
    wheels = list(artifact_dir.glob("flopbench-*.whl"))
    sdists = list(artifact_dir.glob("flopbench-*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise ReleaseError("Release directory must contain exactly one wheel and one sdist")
    validate_cyclonedx(sbom_path, lock_path)
    report_path = artifact_dir / f"flopbench-{__version__}.licenses.json"
    write_json_new(report_path, license_report(lock_path, policy_path))
    write_checksums(artifact_dir)
    verify_checksums(artifact_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Finalize or verify FlopBench RC artifacts.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    finalizer = subparsers.add_parser("finalize")
    finalizer.add_argument("--artifact-dir", type=Path, required=True)
    finalizer.add_argument("--runtime-lock", type=Path, required=True)
    finalizer.add_argument("--license-policy", type=Path, required=True)
    finalizer.add_argument("--sbom", type=Path, required=True)
    verifier = subparsers.add_parser("verify")
    verifier.add_argument("--artifact-dir", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "finalize":
            finalize(
                arguments.artifact_dir,
                arguments.runtime_lock,
                arguments.license_policy,
                arguments.sbom,
            )
        else:
            verify_checksums(arguments.artifact_dir)
    except ReleaseError as exc:
        parser.error(str(exc))


if __name__ == "__main__":  # pragma: no cover - main() is exercised directly
    main()
