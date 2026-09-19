import hashlib
import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHARTER_SHA256 = "09291f685413fe0329dd6f7f237b1e91e040f49060cfebe9821f0ef77d55a725"


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.stage0
def test_s0_t01_python_install_contract_is_pinned() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    assert (ROOT / ".python-version").read_text(encoding="utf-8").strip() == "3.14.6"
    assert project["requires-python"] == ">=3.14,<3.15"
    assert "--hash=sha256:" in _read("requirements/runtime.txt")
    assert "--hash=sha256:" in _read("requirements/dev.txt")
    workflow = _read(".github/workflows/ci.yml")
    assert 'python-version: "3.14.6"' in workflow
    assert "python -m pip install --require-hashes -r requirements/dev.txt" in workflow


@pytest.mark.stage0
def test_s0_t02_web_install_contract_is_pinned() -> None:
    workspace = json.loads(_read("package.json"))
    assert (ROOT / ".nvmrc").read_text(encoding="utf-8").strip() == "24.17.0"
    assert workspace["packageManager"] == "pnpm@11.19.0"
    assert (ROOT / "pnpm-lock.yaml").is_file()
    workflow = _read(".github/workflows/ci.yml")
    assert 'node-version: "24.17.0"' in workflow
    assert 'version: "11.19.0"' in workflow
    assert "pnpm install --frozen-lockfile" in workflow


@pytest.mark.stage0
def test_s0_t03_lint_gate_is_wired_everywhere() -> None:
    assert "def lint(session: nox.Session)" in _read("noxfile.py")
    assert "python -m nox -s lint" in _read(".github/workflows/ci.yml")
    assert "python -m nox -s lint" in _read("Makefile")
    assert '"lint"' in _read("scripts/tasks.ps1")


@pytest.mark.stage0
def test_s0_t04_typecheck_gate_is_wired_everywhere() -> None:
    assert "def typecheck(session: nox.Session)" in _read("noxfile.py")
    assert "python -m nox -s typecheck" in _read(".github/workflows/ci.yml")
    assert "python -m nox -s typecheck" in _read("Makefile")
    assert '"typecheck"' in _read("scripts/tasks.ps1")


@pytest.mark.stage0
def test_s0_t05_smoke_suite_runs_on_windows_and_ubuntu() -> None:
    workflow = _read(".github/workflows/ci.yml")
    assert "ubuntu-latest" in workflow
    assert "windows-latest" in workflow
    assert "python -m nox -s unit contract security" in workflow
    assert (ROOT / "tests" / "unit").is_dir()
    assert (ROOT / "tests" / "contract").is_dir()


@pytest.mark.stage0
def test_s0_t06_license_documents_and_policy_exist() -> None:
    required = {
        "README.md",
        "README.tr.md",
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
        "docs/architecture.md",
        "docs/limitations.md",
        "flopbench künye.md",
        ".github/dependabot.yml",
        ".github/workflows/dependency-review.yml",
    }
    assert all((ROOT / path).is_file() for path in required)
    assert "Apache License" in _read("LICENSE")


@pytest.mark.stage0
@pytest.mark.parametrize(
    "relative_path",
    [
        "README.md",
        "README.tr.md",
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        "CHANGELOG.md",
        "docs/architecture.md",
        "docs/limitations.md",
        "flopbench künye.md",
    ],
)
def test_required_stage_zero_document_exists(relative_path: str) -> None:
    assert (ROOT / relative_path).is_file()


@pytest.mark.stage0
@pytest.mark.parametrize("readme_name", ["README.md", "README.tr.md"])
def test_readme_contains_independence_disclaimer(readme_name: str) -> None:
    content = (ROOT / readme_name).read_text(encoding="utf-8").lower()

    assert "independent" in content or "ba\u011f\u0131ms\u0131z" in content
    assert "official" in content or "resmî" in content
    assert "eligibility" in content


@pytest.mark.stage0
def test_normative_charter_is_unchanged() -> None:
    charter_path = ROOT / "flopbench künye.md"
    charter = charter_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(charter_path.read_bytes()).hexdigest()

    assert charter.startswith("# FlopBench Proje Künyesi")
    assert digest == CHARTER_SHA256
