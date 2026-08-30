from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from flopbench.contracts import BenchmarkReport, ReadinessReport, Receipt
from flopbench.profile_loader import ProfileErrorCode, ProfileLoadError, load_profile
from flopbench.schema_export import SCHEMA_MODELS, schema_bytes

ROOT = Path(__file__).resolve().parents[2]
PROFILE = ROOT / "profiles" / "flop-teaser-0.1.yaml"
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures"

pytestmark = pytest.mark.stage1


def _load_json(path: Path) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def _validate(schema_name: str, instance: dict[str, Any]) -> None:
    schema = _load_json(SCHEMAS / schema_name)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(instance)


def test_s1_t01_valid_teaser_profile_loads() -> None:
    loaded = load_profile(PROFILE)

    assert loaded.profile.id == "flop-teaser-0.1"
    assert loaded.profile.parameters.miner.recommended_vram_bytes == 16 * 1024**3
    assert loaded.profile.parameters.validator.recommended_memory_bytes == 64 * 1024**3
    assert loaded.profile.parameters.validator.recommended_nvme_bytes == 2 * 1024**4
    assert loaded.profile.parameters.validator.recommended_network_bits_per_second == 1_000_000_000
    assert loaded.byte_length == len(PROFILE.read_bytes())


@pytest.mark.parametrize(
    ("fixture", "expected_path"),
    [
        ("invalid-missing-source-url.yaml", "source_url"),
        ("invalid-negative-vram.yaml", "parameters.miner.recommended_vram_bytes"),
        ("invalid-negative-memory.yaml", "parameters.validator.recommended_memory_bytes"),
        ("invalid-unknown-field.yaml", "unexpected"),
    ],
)
def test_s1_t02_t03_t06_invalid_profiles_are_rejected(fixture: str, expected_path: str) -> None:
    with pytest.raises(ProfileLoadError) as caught:
        load_profile(FIXTURES / "profiles" / fixture)

    assert caught.value.code is ProfileErrorCode.VALIDATION_ERROR
    assert expected_path in {issue.path for issue in caught.value.issues}


def test_s1_t04_same_raw_file_has_stable_hash() -> None:
    first = load_profile(PROFILE)
    second = load_profile(PROFILE)

    assert first.sha256 == second.sha256 == sha256(PROFILE.read_bytes()).hexdigest()


def test_s1_t05_content_change_changes_hash(tmp_path: Path) -> None:
    changed = tmp_path / "changed.yaml"
    changed.write_bytes(PROFILE.read_bytes() + b"\n")

    assert load_profile(changed).sha256 != load_profile(PROFILE).sha256


def test_published_schemas_are_valid_and_current() -> None:
    for filename, model in SCHEMA_MODELS.items():
        schema_path = SCHEMAS / filename
        schema = _load_json(schema_path)
        Draft202012Validator.check_schema(schema)
        assert schema_path.read_bytes() == schema_bytes(filename, model)


def test_profile_matches_published_schema() -> None:
    profile_json = load_profile(PROFILE).profile.model_dump(mode="json", by_alias=True)
    _validate("profile-v1.schema.json", profile_json)


def test_s1_t07_readiness_fixture_matches_published_schema() -> None:
    payload = _load_json(FIXTURES / "reports" / "readiness-valid.json")

    _validate("readiness-report-v1.schema.json", payload)
    ReadinessReport.model_validate(payload)


def test_benchmark_fixture_matches_published_schema() -> None:
    payload = _load_json(FIXTURES / "reports" / "benchmark-valid.json")

    _validate("benchmark-report-v1.schema.json", payload)
    BenchmarkReport.model_validate(payload)


def test_s1_t08_receipt_fixture_matches_published_schema() -> None:
    payload = _load_json(FIXTURES / "receipts" / "receipt-valid.json")

    _validate("receipt-v1.schema.json", payload)
    Receipt.model_validate(payload)
