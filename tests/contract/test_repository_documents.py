import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHARTER_SHA256 = "09291f685413fe0329dd6f7f237b1e91e040f49060cfebe9821f0ef77d55a725"


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
