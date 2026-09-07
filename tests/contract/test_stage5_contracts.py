from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from flopbench.benchmark.adapters import DeterministicMockAdapter
from flopbench.benchmark.engine import canonical_benchmark_json, run_benchmark
from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.benchmark.workload import load_workload

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = ROOT / "schemas" / "benchmark-report-v2.schema.json"
WORKLOAD = ROOT / "src" / "flopbench" / "workloads" / "smoke-v1.json"

pytestmark = pytest.mark.stage5


def test_stage5_report_matches_published_v2_schema() -> None:
    fixed = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)
    report = run_benchmark(
        DeterministicMockAdapter(),
        load_workload(WORKLOAD),
        "fixture-model",
        benchmark_id=UUID("018f4cf8-6c40-7b29-9c61-5c120cd9a005"),
        now=lambda: fixed,
    )
    payload = json.loads(canonical_benchmark_json(report))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)
    assert BenchmarkReportV2.model_validate(payload) == report


def test_v1_schema_remains_byte_compatible_fixture_contract() -> None:
    payload = json.loads((ROOT / "fixtures" / "reports" / "benchmark-valid.json").read_text())
    schema = json.loads((ROOT / "schemas" / "benchmark-report-v1.schema.json").read_text())

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(payload)


def test_mock_fixture_is_canonical_and_matches_v2_schema() -> None:
    fixture = ROOT / "fixtures" / "reports" / "benchmark-v2-mock.json"
    raw = fixture.read_text(encoding="utf-8").rstrip("\n")
    report = BenchmarkReportV2.model_validate_json(raw)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))

    Draft202012Validator(schema, format_checker=FormatChecker()).validate(json.loads(raw))
    assert canonical_benchmark_json(report) == raw
