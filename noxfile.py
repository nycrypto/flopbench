from __future__ import annotations

import tempfile

import nox

nox.options.default_venv_backend = "virtualenv"
nox.options.reuse_existing_virtualenvs = True


def install_project(session: nox.Session) -> None:
    session.install("--require-hashes", "-r", "requirements/dev.txt")
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
        "--cov=flopbench",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def contract(session: nox.Session) -> None:
    install_project(session)
    stage_markers = " or ".join(f"stage{stage}" for stage in range(10))
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
        "--cov=flopbench.probe.privacy",
        "--cov=flopbench.benchmark.endpoint",
        "--cov=flopbench.benchmark.transport",
        "--cov=flopbench.benchmark.response_limits",
        "--cov=flopbench.reporting.redaction",
        "--cov=flopbench.receipt.codec",
        "--cov=flopbench.receipt.models",
        "--cov=flopbench.receipt.service",
        "--cov=flopbench.simulator",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=100",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def lint(session: nox.Session) -> None:
    install_project(session)
    session.run("ruff", "check", "src", "tests", "noxfile.py")
    session.run("ruff", "format", "--check", "src", "tests", "noxfile.py")


@nox.session(python="3.14")
def typecheck(session: nox.Session) -> None:
    install_project(session)
    session.run("mypy", "src", "tests")


@nox.session(python="3.14")
def build(session: nox.Session) -> None:
    install_project(session)
    session.run("python", "-m", "build", "--no-isolation")
