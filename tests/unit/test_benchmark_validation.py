from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from flopbench.benchmark.adapters import DeterministicMockAdapter
from flopbench.benchmark.engine import run_benchmark
from flopbench.benchmark.models import BenchmarkMetricSummary, BenchmarkReportV2, BenchmarkRunRecord
from flopbench.benchmark.workload import WorkloadError, WorkloadErrorCode, load_workload
from flopbench.contracts import MetricConfidence

ROOT = Path(__file__).resolve().parents[2]
WORKLOAD = ROOT / "src" / "flopbench" / "workloads" / "smoke-v1.json"


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"\xef\xbb\xbf{}", WorkloadErrorCode.INVALID_ENCODING),
        (b"{}\r\n", WorkloadErrorCode.INVALID_NEWLINE),
        (b"\xff", WorkloadErrorCode.INVALID_ENCODING),
        (b"not-json\n", WorkloadErrorCode.INVALID),
        (b'{"schema":"one","schema":"two"}\n', WorkloadErrorCode.INVALID),
        (b"[" * 5000 + b"0" + b"]" * 5000, WorkloadErrorCode.INVALID),
    ],
)
def test_workload_loader_rejects_unsafe_bytes(
    tmp_path: Path, payload: bytes, code: WorkloadErrorCode
) -> None:
    path = tmp_path / "unsafe.json"
    path.write_bytes(payload)

    with pytest.raises(WorkloadError) as caught:
        load_workload(path)

    assert caught.value.code is code


def test_workload_loader_rejects_missing_and_oversized_files(tmp_path: Path) -> None:
    with pytest.raises(WorkloadError) as missing:
        load_workload(tmp_path / "private-name.json")
    with pytest.raises(WorkloadError) as large:
        load_workload(WORKLOAD, max_bytes=1)

    assert missing.value.code is WorkloadErrorCode.READ_ERROR
    assert "private-name" not in str(missing.value)
    assert large.value.code is WorkloadErrorCode.TOO_LARGE


def test_run_record_requires_metrics_only_for_success() -> None:
    base = {"sequence": 1, "prompt_id": "p", "warmup": False}

    with pytest.raises(ValidationError, match="all core metrics"):
        BenchmarkRunRecord.model_validate({**base, "outcome": "success"})
    with pytest.raises(ValidationError, match="error code"):
        BenchmarkRunRecord.model_validate({**base, "outcome": "timeout"})
    with pytest.raises(ValidationError, match="cannot contain"):
        BenchmarkRunRecord.model_validate(
            {
                **base,
                "outcome": "success",
                "ttft_seconds": 0.1,
                "latency_seconds": 1.0,
                "generated_tokens": 1,
                "tokens_per_second": 1.0,
                "error_code": "benchmark.error",
            }
        )


def test_metric_summary_empty_state_is_consistent() -> None:
    with pytest.raises(ValidationError, match="empty metric"):
        BenchmarkMetricSummary(
            unit="second",
            confidence=MetricConfidence.MEASURED,
            samples=[],
            p50=1.0,
            p95=None,
        )


@pytest.mark.parametrize("mutation", ["sequence", "warmup", "percentile", "samples", "ttft"])
def test_report_rejects_tampered_measurement_accounting(mutation: str) -> None:
    report = run_benchmark(DeterministicMockAdapter(), load_workload(WORKLOAD), "fixture")
    payload = report.model_dump(mode="json", by_alias=True)
    if mutation == "sequence":
        payload["runs"][0]["sequence"] = 99
    elif mutation == "warmup":
        payload["runs"][0]["warmup"] = False
    elif mutation == "percentile":
        payload["metrics"]["latency"]["p95"] = 100.0
    elif mutation == "samples":
        payload["metrics"]["latency"].update(samples=[1.0], p50=1.0, p95=1.0)
    else:
        payload["runs"][0]["ttft_seconds"] = 100.0
    with pytest.raises(ValidationError):
        BenchmarkReportV2.model_validate(payload)
    with pytest.raises(ValidationError, match="require p50"):
        BenchmarkMetricSummary(
            unit="second",
            confidence=MetricConfidence.MEASURED,
            samples=[1.0],
            p50=None,
            p95=None,
        )
