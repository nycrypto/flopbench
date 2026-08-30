from __future__ import annotations

import nox

nox.options.default_venv_backend = "virtualenv"
nox.options.reuse_existing_virtualenvs = True


def install_project(session: nox.Session) -> None:
    session.install("--require-hashes", "-r", "requirements/dev.txt")
    session.install(".", "--no-build-isolation", "--no-deps")


def pytest_isolation_args(session: nox.Session) -> list[str]:
    """Keep pytest temp/cache state private to this Nox session invocation."""

    temporary_directory = session.create_tmp()
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
        "--cov=flopbench",
        "--cov-branch",
        "--cov-report=term-missing",
        "--cov-fail-under=85",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def contract(session: nox.Session) -> None:
    install_project(session)
    session.run(
        "pytest",
        "tests/contract",
        "-m",
        "stage0 or stage1 or stage2 or stage3 or stage4",
        *pytest_isolation_args(session),
    )


@nox.session(python="3.14")
def security(session: nox.Session) -> None:
    install_project(session)
    session.run(
        "pytest",
        "tests/security",
        "--cov=flopbench.probe.privacy",
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
