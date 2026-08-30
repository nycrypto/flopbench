from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from flopbench.contracts import BenchmarkReport, ReadinessReport, SourceProfile
from flopbench.profile_loader import ProfileErrorCode, ProfileLoadError, load_profile
from flopbench.schema_export import SCHEMA_MODELS, export_schemas, schema_bytes

ROOT = Path(__file__).resolve().parents[2]
VALID_PROFILE = ROOT / "profiles" / "flop-teaser-0.1.yaml"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"\xef\xbb\xbfschema: value\n", ProfileErrorCode.INVALID_ENCODING),
        (b"schema: value\r\n", ProfileErrorCode.INVALID_NEWLINE),
        (b"\xff", ProfileErrorCode.INVALID_ENCODING),
        (b"schema: [\n", ProfileErrorCode.YAML_PARSE_ERROR),
        (b"schema: one\nschema: two\n", ProfileErrorCode.DUPLICATE_FIELD),
    ],
)
def test_loader_rejects_unsafe_serializations(
    tmp_path: Path, payload: bytes, code: ProfileErrorCode
) -> None:
    path = tmp_path / "unsafe.yaml"
    path.write_bytes(payload)

    with pytest.raises(ProfileLoadError) as caught:
        load_profile(path)

    assert caught.value.code is code
    assert str(caught.value)


def test_loader_rejects_oversized_profile(tmp_path: Path) -> None:
    path = tmp_path / "large.yaml"
    path.write_bytes(b"ab")

    with pytest.raises(ProfileLoadError) as caught:
        load_profile(path, max_bytes=1)

    assert caught.value.code is ProfileErrorCode.TOO_LARGE


def test_loader_reports_read_error_without_path_disclosure(tmp_path: Path) -> None:
    missing = tmp_path / "secret-name.yaml"

    with pytest.raises(ProfileLoadError) as caught:
        load_profile(missing)

    assert caught.value.code is ProfileErrorCode.READ_ERROR
    assert "secret-name" not in str(caught.value)


def test_validation_error_contains_only_path_and_kind() -> None:
    path = ROOT / "fixtures" / "profiles" / "invalid-missing-source-url.yaml"

    with pytest.raises(ProfileLoadError) as caught:
        load_profile(path)

    assert caught.value.issues
    assert caught.value.issues[0].path == "source_url"
    assert caught.value.issues[0].kind == "missing"


def test_readiness_model_rejects_inconsistent_summary() -> None:
    fixture_path = ROOT / "fixtures" / "reports" / "readiness-valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["summary"]["fail"] = 0

    with pytest.raises(ValidationError, match="summary total"):
        ReadinessReport.model_validate(payload)


def test_readiness_model_requires_utc() -> None:
    fixture_path = ROOT / "fixtures" / "reports" / "readiness-valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["created_at"] = "2026-08-30T12:00:00+03:00"

    with pytest.raises(ValidationError, match="timestamp must use UTC"):
        ReadinessReport.model_validate(payload)


def test_benchmark_model_rejects_negative_duration() -> None:
    fixture_path = ROOT / "fixtures" / "reports" / "benchmark-valid.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["finished_at"] = "2026-08-30T08:59:59Z"

    with pytest.raises(ValidationError, match="finished_at"):
        BenchmarkReport.model_validate(payload)


def test_source_profile_rejects_retrieval_before_source_update() -> None:
    loaded = load_profile(VALID_PROFILE)
    payload = loaded.profile.model_dump(by_alias=True)
    payload["retrieved_at"] = payload["source_updated_at"].replace(year=2025)

    with pytest.raises(ValidationError, match="retrieved_at"):
        SourceProfile.model_validate(payload)


def test_schema_export_writes_exact_generated_bytes(tmp_path: Path) -> None:
    export_schemas(tmp_path)

    for filename, model in SCHEMA_MODELS.items():
        assert (tmp_path / filename).read_bytes() == schema_bytes(filename, model)
