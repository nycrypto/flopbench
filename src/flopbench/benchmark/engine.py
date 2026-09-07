"""Deterministic benchmark orchestration and complete failure accounting."""

from __future__ import annotations

import math
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from threading import Event
from uuid import UUID, uuid4

from flopbench import __version__
from flopbench.benchmark.adapters import (
    AdapterCancelledError,
    AdapterError,
    AdapterPartialError,
    AdapterRequest,
    AdapterSample,
    AdapterTimeoutError,
    BenchmarkAdapter,
)
from flopbench.benchmark.models import (
    BenchmarkMetricSummary,
    BenchmarkMetricsV2,
    BenchmarkOutcome,
    BenchmarkOutcomeSummary,
    BenchmarkReportV2,
    BenchmarkRunRecord,
    BenchmarkWorkloadIdentity,
)
from flopbench.benchmark.vram import VramObserver
from flopbench.benchmark.workload import LoadedWorkload
from flopbench.contracts import MetricConfidence
from flopbench.validator_doctor.metrics import nearest_rank


class BenchmarkCancelledError(RuntimeError):
    """Raised after adapter cleanup when the user cancels a benchmark."""


def _metric(samples: list[float], unit: str) -> BenchmarkMetricSummary:
    return BenchmarkMetricSummary(
        unit=unit,
        confidence=MetricConfidence.MEASURED,
        samples=samples,
        p50=nearest_rank(samples, 50) if samples else None,
        p95=nearest_rank(samples, 95) if samples else None,
    )


def _record(
    sequence: int,
    prompt_id: str,
    warmup: bool,
    outcome: BenchmarkOutcome,
    sample: AdapterSample | None = None,
    error_code: str | None = None,
    peak_vram_bytes: int | None = None,
) -> BenchmarkRunRecord:
    return BenchmarkRunRecord(
        sequence=sequence,
        prompt_id=prompt_id,
        warmup=warmup,
        outcome=outcome,
        ttft_seconds=sample.ttft_seconds if sample else None,
        latency_seconds=sample.latency_seconds if sample else None,
        generated_tokens=sample.generated_tokens if sample else None,
        tokens_per_second=sample.tokens_per_second if sample else None,
        peak_vram_bytes=peak_vram_bytes,
        error_code=error_code,
        raw_response_sha256=sha256(sample.raw_response).hexdigest() if sample else None,
    )


def run_benchmark(
    adapter: BenchmarkAdapter,
    workload: LoadedWorkload,
    model: str,
    *,
    timeout_seconds: float = 60.0,
    cancel: Event | None = None,
    benchmark_id: UUID | None = None,
    now: Callable[[], datetime] | None = None,
    vram_observer: VramObserver | None = None,
) -> BenchmarkReportV2:
    """Run warmups then measured requests; always close the adapter."""

    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be finite and positive")
    cancellation = cancel or Event()
    clock = now or (lambda: datetime.now(UTC))
    started_at = clock()
    records: list[BenchmarkRunRecord] = []
    definition = workload.definition
    total = definition.warmup_runs + definition.measured_runs
    try:
        model_identity = adapter.model_identity(model)
        for offset in range(total):
            warmup = offset < definition.warmup_runs
            prompt = definition.prompts[offset % len(definition.prompts)]
            if cancellation.is_set():
                raise BenchmarkCancelledError("Benchmark cancelled by user")
            request = AdapterRequest(
                prompt=prompt.prompt,
                max_tokens=prompt.max_tokens,
                seed=definition.seed + offset,
                timeout_seconds=timeout_seconds,
            )
            if vram_observer is not None:
                vram_observer.start()
            sample: AdapterSample | None = None
            outcome = BenchmarkOutcome.SUCCESS
            error_code: str | None = None
            cancelled_error: AdapterCancelledError | None = None
            try:
                sample = adapter.run(request, cancellation)
            except AdapterPartialError as exc:
                outcome = BenchmarkOutcome.PARTIAL
                sample = exc.sample
                error_code = exc.code
            except AdapterTimeoutError as exc:
                outcome = BenchmarkOutcome.TIMEOUT
                error_code = exc.code
            except AdapterCancelledError as exc:
                cancelled_error = exc
            except AdapterError as exc:
                outcome = BenchmarkOutcome.ERROR
                error_code = exc.code
            finally:
                peak_vram_bytes = vram_observer.stop() if vram_observer is not None else None
            if cancelled_error is not None:
                raise BenchmarkCancelledError("Benchmark cancelled by user") from cancelled_error
            records.append(
                _record(
                    offset + 1,
                    prompt.id,
                    warmup,
                    outcome,
                    sample,
                    error_code,
                    peak_vram_bytes,
                )
            )
    finally:
        adapter.close()

    measured = [record for record in records if not record.warmup]
    successful = [record for record in measured if record.outcome is BenchmarkOutcome.SUCCESS]
    counts = dict.fromkeys(BenchmarkOutcome, 0)
    for record in measured:
        counts[record.outcome] += 1
    failed_count = len(measured) - counts[BenchmarkOutcome.SUCCESS]
    vram_samples = [
        float(record.peak_vram_bytes) for record in successful if record.peak_vram_bytes is not None
    ]
    return BenchmarkReportV2(
        schema="flopbench-benchmark-report-v2",
        benchmark_id=benchmark_id or uuid4(),
        adapter=adapter.identity,
        model=model_identity,
        workload=BenchmarkWorkloadIdentity(
            id=definition.id,
            version=definition.version,
            sha256=workload.sha256,
            warmup_runs=definition.warmup_runs,
            measured_runs=definition.measured_runs,
        ),
        runs=records,
        metrics=BenchmarkMetricsV2(
            ttft=_metric(
                [record.ttft_seconds for record in successful if record.ttft_seconds is not None],
                "second",
            ),
            tokens_per_second=_metric(
                [
                    record.tokens_per_second
                    for record in successful
                    if record.tokens_per_second is not None
                ],
                "token/second",
            ),
            latency=_metric(
                [
                    record.latency_seconds
                    for record in successful
                    if record.latency_seconds is not None
                ],
                "second",
            ),
            peak_vram=_metric(vram_samples, "byte"),
        ),
        outcomes=BenchmarkOutcomeSummary(
            success=counts[BenchmarkOutcome.SUCCESS],
            timeout=counts[BenchmarkOutcome.TIMEOUT],
            error=counts[BenchmarkOutcome.ERROR],
            cancelled=counts[BenchmarkOutcome.CANCELLED],
            partial=counts[BenchmarkOutcome.PARTIAL],
            error_rate=failed_count / len(measured),
        ),
        started_at=started_at,
        finished_at=clock(),
        tool_version=__version__,
    )


def canonical_benchmark_json(report: BenchmarkReportV2) -> str:
    payload = report.model_dump(mode="json", by_alias=True, exclude_none=False)
    import json

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
