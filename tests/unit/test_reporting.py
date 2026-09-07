from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from flopbench.benchmark.models import BenchmarkModelIdentity, BenchmarkReportV2
from flopbench.cli import app
from flopbench.contracts import PrivacyLevel
from flopbench.profile_loader import load_profile
from flopbench.reporting import compare as compare_module
from flopbench.reporting.canonical import canonical_bytes, canonical_digest, parse_json
from flopbench.reporting.compare import compare_benchmarks, diff_exports
from flopbench.reporting.errors import ReportError
from flopbench.reporting.models import ReportExport
from flopbench.reporting.render import render_html, render_json, render_terminal
from flopbench.reporting.service import create_export, load_export, load_report, write_new_file

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "fixtures" / "reports"
PROFILE = ROOT / "profiles" / "flop-teaser-0.1.yaml"


def benchmark_export() -> ReportExport:
    return create_export(
        load_report(REPORTS / "benchmark-v2-mock.json"),
        PrivacyLevel.PUBLIC,
        profile=load_profile(PROFILE),
    )


def test_jcs_is_order_independent_and_metric_sensitive() -> None:
    left = parse_json(b'{"z":1,"a":{"b":2}}')
    right = parse_json(b'{"a":{"b":2},"z":1}')

    assert canonical_bytes(left) == canonical_bytes(right)
    assert canonical_digest(left) == canonical_digest(right)
    assert canonical_digest(left) != canonical_digest({"z": 2, "a": {"b": 2}})


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b'{"a":1,"a":2}', "report.invalid_json"),
        (b'{"value":NaN}', "report.invalid_json"),
        (b"[]", "report.invalid_json"),
        (b'"unterminated', "report.invalid_json"),
        (b'{"value":9007199254740992}', "report.invalid_canonical_value"),
    ],
)
def test_strict_json_rejects_ambiguous_values(raw: bytes, code: str) -> None:
    with pytest.raises(ReportError) as caught:
        parse_json(raw)
    assert caught.value.code == code


def test_export_round_trip_digest_and_renderers(tmp_path: Path) -> None:
    export = benchmark_export()
    first = render_json(export)
    second = render_json(ReportExport.model_validate_json(first))
    path = tmp_path / "report.json"
    write_new_file(path, first)

    assert first == second
    assert load_export(path) == export
    assert export.digest.value in render_terminal(export)
    assert b"default-src 'none'" in render_html(export)
    with pytest.raises(ReportError, match="already exists"):
        write_new_file(path, first)


def test_html_escapes_untrusted_model_name() -> None:
    source = load_report(REPORTS / "benchmark-v2-mock.json")
    assert isinstance(source, BenchmarkReportV2)
    malicious = source.model_copy(
        update={
            "model": BenchmarkModelIdentity(
                name='<script>alert("x")</script>', digest=source.model.digest
            )
        }
    )
    rendered = render_html(
        create_export(malicious, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))
    )

    assert b"<script" not in rendered.lower()
    assert b"&lt;script&gt;" in rendered
    assert b" src=" not in rendered.lower()
    assert b" href=" not in rendered.lower()


def test_diff_and_compatible_comparison() -> None:
    left = benchmark_export()
    payload = left.document.payload
    assert isinstance(payload, BenchmarkReportV2)
    changed_metric = payload.metrics.ttft.model_copy(
        update={"samples": [0.062, 0.063, 0.064], "p50": 0.063, "p95": 0.064}
    )
    changed_runs = [
        run.model_copy(update={"ttft_seconds": run.ttft_seconds + 0.01})
        if not run.warmup and run.ttft_seconds is not None
        else run
        for run in payload.runs
    ]
    changed = BenchmarkReportV2.model_validate(
        payload.model_dump(mode="python", by_alias=True)
        | {
            "runs": changed_runs,
            "metrics": payload.metrics.model_copy(update={"ttft": changed_metric}),
        }
    )
    right = create_export(changed, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))

    difference = diff_exports(left, right)
    comparison = compare_benchmarks(left, right)
    assert any(change.path.endswith("/metrics/ttft/p50") for change in difference.changes)
    assert not difference.truncated
    assert comparison.compatible
    assert comparison.metrics[0].absolute_delta == pytest.approx(0.01)


def test_incompatible_workload_is_not_ranked() -> None:
    left = benchmark_export()
    payload = left.document.payload
    assert isinstance(payload, BenchmarkReportV2)
    altered = payload.model_copy(
        update={"workload": payload.workload.model_copy(update={"id": "other"})}
    )
    right = create_export(altered, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE))

    result = compare_benchmarks(left, right)

    assert not result.compatible
    assert result.metrics == []
    assert "comparison.workload_mismatch" in result.reason_codes


def test_diff_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    left = benchmark_export()
    right = left.model_copy(
        update={
            "document": left.document.model_copy(
                update={"payload": left.document.payload.model_copy(update={"runs": []})}
            )
        }
    )
    monkeypatch.setattr(compare_module, "MAX_DIFF_CHANGES", 1)
    result = diff_exports(left, right)
    assert len(result.changes) == 1
    assert result.truncated


def test_missing_profile_and_changed_runtime_or_model_are_incompatible() -> None:
    source = load_report(REPORTS / "benchmark-v2-mock.json")
    assert isinstance(source, BenchmarkReportV2)
    no_profile = create_export(source, PrivacyLevel.PUBLIC)
    reference = benchmark_export()
    missing = compare_benchmarks(no_profile, reference)
    assert "comparison.profile_missing" in missing.reason_codes

    changed = source.model_copy(
        update={
            "adapter": source.adapter.model_copy(update={"runtime_version": "2.0.0"}),
            "model": source.model.model_copy(update={"name": "different-model"}),
        }
    )
    mismatch = compare_benchmarks(
        reference,
        create_export(changed, PrivacyLevel.PUBLIC, profile=load_profile(PROFILE)),
    )
    assert "comparison.adapter_mismatch" in mismatch.reason_codes
    assert "comparison.model_mismatch" in mismatch.reason_codes


def test_load_errors_are_safe_and_bounded(tmp_path: Path) -> None:
    missing = tmp_path / "SECRET-name.json"
    with pytest.raises(ReportError) as caught:
        load_report(missing)
    assert "SECRET-name" not in str(caught.value)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * 11)
    with pytest.raises(ReportError) as caught:
        load_report(oversized, max_bytes=10)
    assert caught.value.code == "report.too_large"

    unsupported = tmp_path / "unsupported.json"
    unsupported.write_text('{"schema":"unknown"}', encoding="utf-8")
    with pytest.raises(ReportError) as caught:
        load_report(unsupported)
    assert caught.value.code == "report.unsupported_schema"


def test_cli_public_write_requires_matching_preview(tmp_path: Path) -> None:
    runner = CliRunner()
    source = REPORTS / "benchmark-v2-mock.json"
    preview = runner.invoke(
        app,
        ["report", "export", str(source), "--privacy", "public", "--profile", str(PROFILE)],
    )
    digest = json.loads(preview.stdout)["digest"]["value"]
    output = tmp_path / "public.json"

    denied = runner.invoke(
        app,
        [
            "report",
            "export",
            str(source),
            "--privacy",
            "public",
            "--profile",
            str(PROFILE),
            "--output",
            str(output),
        ],
    )
    assert denied.exit_code == 2
    assert not output.exists()
    accepted = runner.invoke(
        app,
        [
            "report",
            "export",
            str(source),
            "--privacy",
            "public",
            "--profile",
            str(PROFILE),
            "--output",
            str(output),
            "--confirm-preview",
            digest,
        ],
    )

    assert preview.exit_code == 0
    assert accepted.exit_code == 0
    assert load_export(output).digest.value == digest


def test_export_model_rejects_tampered_digest() -> None:
    data = json.loads(render_json(benchmark_export()))
    data["digest"]["value"] = "0" * 64
    with pytest.raises(ValidationError, match="digest mismatch"):
        ReportExport.model_validate(data)
