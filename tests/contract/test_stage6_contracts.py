from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from flopbench.benchmark.models import BenchmarkReportV2
from flopbench.contracts import PrivacyLevel
from flopbench.probe.service import run_fixture_probe
from flopbench.profile_loader import load_profile
from flopbench.reporting.canonical import canonical_digest, parse_json
from flopbench.reporting.compare import compare_benchmarks
from flopbench.reporting.models import ReportExport
from flopbench.reporting.render import render_html, render_json
from flopbench.reporting.service import create_export, load_report

ROOT = Path(__file__).resolve().parents[2]
BENCHMARK = ROOT / "fixtures" / "reports" / "benchmark-v2-mock.json"
PROFILE = ROOT / "profiles" / "flop-teaser-0.1.yaml"
pytestmark = pytest.mark.stage6


def _public_benchmark() -> ReportExport:
    return create_export(
        load_report(BENCHMARK),
        PrivacyLevel.PUBLIC,
        profile=load_profile(PROFILE),
    )


def test_s6_t01_public_secret_trap_contains_no_secret() -> None:
    source = run_fixture_probe(
        ROOT / "fixtures" / "hardware" / "secret-leak-trap.json",
        PrivacyLevel.PRIVATE,
    )
    rendered = render_json(create_export(source, PrivacyLevel.PUBLIC)).lower()

    assert b"secret-" not in rendered
    assert b"token-secret" not in rendered
    assert b"private key" not in rendered


def test_s6_t02_same_report_has_same_canonical_digest() -> None:
    assert render_json(_public_benchmark()) == render_json(_public_benchmark())


def test_s6_t03_field_order_does_not_change_digest(tmp_path: Path) -> None:
    original = json.loads(BENCHMARK.read_text("utf-8"))
    reordered = dict(reversed(list(original.items())))
    alternate = tmp_path / "reordered.json"
    alternate.write_text(json.dumps(reordered), encoding="utf-8")

    first = _public_benchmark()
    second = create_export(
        load_report(alternate), PrivacyLevel.PUBLIC, profile=load_profile(PROFILE)
    )

    assert first.digest == second.digest


def test_s6_t04_one_metric_change_changes_digest() -> None:
    baseline = _public_benchmark()
    payload = baseline.document.payload
    assert isinstance(payload, BenchmarkReportV2)
    changed_runs = [
        run.model_copy(update={"ttft_seconds": run.ttft_seconds + 0.01})
        if not run.warmup and run.ttft_seconds is not None
        else run
        for run in payload.runs
    ]
    changed = payload.model_copy(
        update={
            "runs": changed_runs,
            "metrics": payload.metrics.model_copy(
                update={
                    "ttft": payload.metrics.ttft.model_copy(
                        update={"samples": [0.062, 0.063, 0.064], "p50": 0.063, "p95": 0.064}
                    )
                }
            ),
        }
    )

    changed_export = create_export(changed, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))
    assert baseline.digest.value != changed_export.digest.value


def test_s6_t05_model_name_is_escaped_in_html() -> None:
    source = load_report(BENCHMARK)
    assert isinstance(source, BenchmarkReportV2)
    hostile = source.model_copy(
        update={"model": source.model.model_copy(update={"name": "<script>alert(1)</script>"})}
    )

    rendered = render_html(
        create_export(hostile, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))
    ).lower()

    assert b"<script" not in rendered
    assert b"&lt;script&gt;" in rendered


def test_s6_t06_different_workload_is_not_ranked() -> None:
    left = _public_benchmark()
    payload = left.document.payload
    assert isinstance(payload, BenchmarkReportV2)
    incompatible = payload.model_copy(
        update={"workload": payload.workload.model_copy(update={"id": "different-workload"})}
    )
    right = create_export(incompatible, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))

    comparison = compare_benchmarks(left, right)

    assert not comparison.compatible
    assert comparison.metrics == []
    assert "comparison.workload_mismatch" in comparison.reason_codes


def test_s6_t07_html_is_standalone_and_offline() -> None:
    rendered = render_html(_public_benchmark()).lower()

    assert b"<script" not in rendered
    assert b" src=" not in rendered
    assert b" href=" not in rendered
    assert b"http://" not in rendered
    assert b"https://" not in rendered


def test_s6_t08_public_export_validates_published_schema() -> None:
    schema = json.loads((ROOT / "schemas" / "report-export-v1.schema.json").read_text("utf-8"))
    export = _public_benchmark()

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(json.loads(render_json(export)))


def test_jcs_digest_is_over_document_not_rendering() -> None:
    export = _public_benchmark()
    assert export.digest.value == canonical_digest(
        export.document.model_dump(mode="json", by_alias=True)
    )
    assert parse_json(render_json(export))["digest"]["scope"] == "document"
