from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from flopbench.contracts import PrivacyLevel
from flopbench.probe.models import GpuStatus
from flopbench.probe.service import (
    ProbeError,
    ProbeErrorCode,
    canonical_probe_json,
    run_fixture_probe,
)

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "fixtures" / "hardware"

pytestmark = pytest.mark.stage2


@pytest.mark.parametrize(
    ("fixture", "expected_vram"),
    [
        ("windows-nvidia-24gb.json", 24 * 1024**3),
        ("linux-nvidia-16gb.json", 16 * 1024**3),
    ],
)
def test_s2_t01_t02_nvidia_vram_is_normalized(fixture: str, expected_vram: int) -> None:
    report = run_fixture_probe(HARDWARE / fixture, PrivacyLevel.PRIVATE)

    assert report.gpu.status is GpuStatus.DETECTED
    assert report.gpu.devices[0].vendor == "NVIDIA"
    assert report.gpu.devices[0].vram_total_bytes == expected_vram


def test_amd_fixture_uses_safe_provider_contract() -> None:
    report = run_fixture_probe(HARDWARE / "linux-amd-16gb.json", PrivacyLevel.PRIVATE)

    assert report.gpu.status is GpuStatus.DETECTED
    assert report.gpu.devices[0].vendor == "AMD"


def test_s2_t03_cpu_only_does_not_crash() -> None:
    report = run_fixture_probe(HARDWARE / "cpu-only.json", PrivacyLevel.PRIVATE)

    assert report.gpu.status is GpuStatus.NO_SUPPORTED_GPU
    assert report.gpu.devices == []


@pytest.mark.parametrize(
    ("fixture", "status"),
    [
        ("missing-driver.json", GpuStatus.UNKNOWN),
        ("unsupported-gpu.json", GpuStatus.UNSUPPORTED),
    ],
)
def test_s2_t04_missing_or_unsupported_driver_is_safe(fixture: str, status: GpuStatus) -> None:
    assert run_fixture_probe(HARDWARE / fixture, PrivacyLevel.PRIVATE).gpu.status is status


def test_s2_t05_malformed_provider_is_controlled() -> None:
    with pytest.raises(ProbeError) as caught:
        run_fixture_probe(HARDWARE / "malformed-provider-output.json", PrivacyLevel.PRIVATE)

    assert caught.value.code is ProbeErrorCode.PROVIDER_MALFORMED


def test_s2_t08_static_fixture_output_is_byte_deterministic() -> None:
    path = HARDWARE / "windows-nvidia-24gb.json"

    first = canonical_probe_json(run_fixture_probe(path, PrivacyLevel.PRIVATE))
    second = canonical_probe_json(run_fixture_probe(path, PrivacyLevel.PRIVATE))

    assert first.encode() == second.encode()


def test_probe_report_matches_published_schema() -> None:
    report = run_fixture_probe(HARDWARE / "cpu-only.json", PrivacyLevel.PUBLIC)
    schema: dict[str, Any] = json.loads((ROOT / "schemas" / "probe-v1.schema.json").read_text())

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(
        report.model_dump(mode="json", by_alias=True, exclude_none=True)
    )


def test_stage2_privacy_document_exists() -> None:
    assert (ROOT / "docs" / "privacy.md").is_file()
