from __future__ import annotations

import tempfile
from pathlib import Path

import nox

nox.options.default_venv_backend = "virtualenv"
nox.options.reuse_existing_virtualenvs = True


def install_project(session: nox.Session) -> None:
    session.install("--require-hashes", "-r", "requirements/dev.txt")
    session.install(".", "--no-build-isolation", "--no-deps")


def prepare_build(session: nox.Session) -> None:
    """Install build tools and verify assets before installing the local package."""

    session.install("--require-hashes", "-r", "requirements/dev.txt")
    session.run(
        "corepack",
        "pnpm",
        "--filter",
        "@flopbench/web",
        "build",
        external=True,
        env={"CI": "true"},
    )
    session.run("python", "scripts/sync_web_assets.py", "--check")
    session.install(".", "--no-build-isolation", "--no-deps")


def pytest_isolation_args(session: nox.Session) -> list[str]:
    """Keep pytest temp/cache state private to this Nox session invocation."""

    temporary_directory = tempfile.mkdtemp(prefix=f"flopbench-{session.name}-")
    return [
        "--basetemp",
        f"{temporary_directory}/pytest",
        "-o",
        f"cache_dir={temporary_directory}/cache",
    ]


@nox.session(python="3.14")
def unit(session: nox.Session) -> None:
    install_project(session)
    session.run(
        "pytest",
        "tests/unit",
        "tests/contract/test_stage7_api.py",
        "tests/contract/test_stage8_receipts.py",
        "tests/contract/test_stage9_simulator.py",
        "tests/contract/test_stage9_api.py",
        "tests/contract/test_stage10_release.py",
        "--cov=flopbench",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def contract(session: nox.Session) -> None:
    install_project(session)
    stage_markers = " or ".join(f"stage{stage}" for stage in range(11))
    session.run(
        "pytest",
        "tests/contract",
        "-m",
        stage_markers,
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def security(session: nox.Session) -> None:
    install_project(session)
    session.run(
        "pytest",
        "tests/security",
        "tests/unit/test_benchmark_transport.py",
        "tests/unit/test_benchmark_response_limits.py",
        "tests/unit/test_receipt.py",
        "tests/contract/test_stage8_receipts.py",
        "tests/unit/test_simulator.py",
        "tests/contract/test_stage9_simulator.py",
        "tests/contract/test_stage10_release.py",
        "--cov=flopbench.probe.privacy",
        "--cov=flopbench.benchmark.endpoint",
        "--cov=flopbench.benchmark.transport",
        "--cov=flopbench.benchmark.response_limits",
        "--cov=flopbench.reporting.redaction",
        "--cov=flopbench.receipt.codec",
        "--cov=flopbench.receipt.models",
        "--cov=flopbench.receipt.service",
        "--cov=flopbench.simulator",
        "--cov=flopbench.config",
        "--cov=flopbench.release",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def lint(session: nox.Session) -> None:
    install_project(session)
    session.run("ruff", "check", "src", "tests", "scripts", "noxfile.py")
    session.run("ruff", "format", "--check", "src", "tests", "scripts", "noxfile.py")


@nox.session(python="3.14")
def typecheck(session: nox.Session) -> None:
    install_project(session)
    session.run("mypy", "src", "tests", "scripts")


@nox.session(python="3.14")
def build(session: nox.Session) -> None:
    prepare_build(session)
    session.run("python", "-m", "build", "--no-isolation")


@nox.session(name="install", python="3.14")
def install_candidate(session: nox.Session) -> None:
    """Build and install the wheel in a new venv on the current CI platform."""

    prepare_build(session)
    artifact_dir = Path(tempfile.mkdtemp(prefix="flopbench-install-artifacts-"))
    session.run("python", "-m", "build", "--no-isolation", "--outdir", str(artifact_dir))
    wheels = list(artifact_dir.glob("flopbench-*.whl"))
    if len(wheels) != 1:
        session.error("Clean-install gate requires exactly one wheel")
    session.run(
        "python",
        "scripts/verify_install.py",
        "--wheel",
        str(wheels[0]),
        "--runtime-lock",
        "requirements/runtime.txt",
        "--expected-version",
        "0.8.0",
    )


@nox.session(python="3.14")
def audit(session: nox.Session) -> None:
    """Audit locked runtime dependencies and tracked files."""

    session.install("--require-hashes", "-r", "requirements/release.txt")
    session.run("pip-audit", "--strict", "--require-hashes", "-r", "requirements/runtime.txt")
    session.run("python", "scripts/check_secrets.py", "--baseline", ".secrets.baseline")


@nox.session(python="3.14")
def release(session: nox.Session) -> None:
    """Produce one checksummed wheel/sdist, CycloneDX SBOM, and license report."""

    prepare_build(session)
    session.install("--require-hashes", "-r", "requirements/release.txt")
    artifact_dir = Path(session.posargs[0] if session.posargs else "dist/release").resolve()
    if artifact_dir.exists():
        session.error(f"Release directory already exists: {artifact_dir}")
    artifact_dir.mkdir(parents=True)
    session.run("python", "-m", "build", "--no-isolation", "--outdir", str(artifact_dir))
    sbom = artifact_dir / "flopbench-0.8.0.cdx.json"
    session.run(
        "pip-audit",
        "--strict",
        "--require-hashes",
        "-r",
        "requirements/runtime.txt",
        "--format",
        "cyclonedx-json",
        "--output",
        str(sbom),
    )
    session.run("python", "scripts/check_secrets.py", "--baseline", ".secrets.baseline")
    session.run(
        "python",
        "-m",
        "flopbench.release",
        "finalize",
        "--artifact-dir",
        str(artifact_dir),
        "--runtime-lock",
        "requirements/runtime.txt",
        "--license-policy",
        "release/license-policy.json",
        "--sbom",
        str(sbom),
    )
    session.run(
        "python",
        "-m",
        "flopbench.release",
        "verify",
        "--artifact-dir",
        str(artifact_dir),
    )
