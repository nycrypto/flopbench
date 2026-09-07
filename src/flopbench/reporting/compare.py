"""Bounded structural diff and compatibility-aware benchmark comparison."""

from __future__ import annotations

import math
from typing import Any, Literal

from flopbench.benchmark.models import BenchmarkReportV2

from .models import (
    BenchmarkComparison,
    MetricComparison,
    ReportChange,
    ReportDiff,
    ReportExport,
)

MAX_DIFF_CHANGES = 500


def diff_exports(left: ReportExport, right: ReportExport) -> ReportDiff:
    changes: list[ReportChange] = []
    truncated = False

    def add(change: ReportChange) -> None:
        nonlocal truncated
        if len(changes) >= MAX_DIFF_CHANGES:
            truncated = True
            return
        changes.append(change)

    def walk(before: Any, after: Any, path: str) -> None:
        nonlocal truncated
        if len(changes) >= MAX_DIFF_CHANGES:
            truncated = True
            return
        if isinstance(before, dict) and isinstance(after, dict):
            for key in sorted(before.keys() | after.keys()):
                child = f"{path}/{key}"
                if key not in before:
                    add(ReportChange(path=child, kind="added", after=after[key]))
                elif key not in after:
                    add(ReportChange(path=child, kind="removed", before=before[key]))
                else:
                    walk(before[key], after[key], child)
            return
        if isinstance(before, list) and isinstance(after, list):
            for index in range(max(len(before), len(after))):
                child = f"{path}/{index}"
                if index >= len(before):
                    add(ReportChange(path=child, kind="added", after=after[index]))
                elif index >= len(after):
                    add(ReportChange(path=child, kind="removed", before=before[index]))
                else:
                    walk(before[index], after[index], child)
            return
        if before != after:
            add(ReportChange(path=path or "/", kind="changed", before=before, after=after))

    walk(
        left.document.model_dump(mode="json", by_alias=True),
        right.document.model_dump(mode="json", by_alias=True),
        "",
    )
    return ReportDiff(
        schema="flopbench-report-diff-v1",
        left_digest=left.digest.value,
        right_digest=right.digest.value,
        truncated=truncated,
        changes=changes,
    )


def compare_benchmarks(left: ReportExport, right: ReportExport) -> BenchmarkComparison:
    reasons: list[str] = []
    left_payload = left.document.payload
    right_payload = right.document.payload
    if not isinstance(left_payload, BenchmarkReportV2) or not isinstance(
        right_payload, BenchmarkReportV2
    ):
        reasons.append("comparison.requires_benchmark_v2")
    if left.document.comparison_profile is None or right.document.comparison_profile is None:
        reasons.append("comparison.profile_missing")
    elif left.document.comparison_profile != right.document.comparison_profile:
        reasons.append("comparison.profile_mismatch")
    if isinstance(left_payload, BenchmarkReportV2) and isinstance(right_payload, BenchmarkReportV2):
        if left_payload.workload != right_payload.workload:
            reasons.append("comparison.workload_mismatch")
        if left_payload.adapter != right_payload.adapter:
            reasons.append("comparison.adapter_mismatch")
        if left_payload.model != right_payload.model:
            reasons.append("comparison.model_mismatch")
        for name in ("ttft", "tokens_per_second", "latency", "peak_vram"):
            left_metric = getattr(left_payload.metrics, name)
            right_metric = getattr(right_payload.metrics, name)
            if (
                left_metric.unit != right_metric.unit
                or left_metric.confidence != right_metric.confidence
            ):
                reasons.append(f"comparison.metric_context_mismatch.{name}")
    if reasons:
        return BenchmarkComparison(
            schema="flopbench-benchmark-comparison-v1",
            compatible=False,
            reason_codes=sorted(set(reasons)),
            left_digest=left.digest.value,
            right_digest=right.digest.value,
            metrics=[],
        )
    assert isinstance(left_payload, BenchmarkReportV2)
    assert isinstance(right_payload, BenchmarkReportV2)
    metrics: list[MetricComparison] = []
    metric_names: tuple[Literal["ttft", "tokens_per_second", "latency", "peak_vram"], ...] = (
        "ttft",
        "tokens_per_second",
        "latency",
        "peak_vram",
    )
    for name in metric_names:
        left_metric = getattr(left_payload.metrics, name)
        right_metric = getattr(right_payload.metrics, name)
        delta = (
            None
            if left_metric.p50 is None or right_metric.p50 is None
            else right_metric.p50 - left_metric.p50
        )
        relative = (
            None if delta is None or left_metric.p50 in (None, 0) else delta / left_metric.p50 * 100
        )
        if (delta is not None and not math.isfinite(delta)) or (
            relative is not None and not math.isfinite(relative)
        ):
            return BenchmarkComparison(
                schema="flopbench-benchmark-comparison-v1",
                compatible=False,
                reason_codes=[f"comparison.metric_delta_non_finite.{name}"],
                left_digest=left.digest.value,
                right_digest=right.digest.value,
                metrics=[],
            )
        metrics.append(
            MetricComparison(
                metric=name,
                unit=left_metric.unit,
                left_p50=left_metric.p50,
                right_p50=right_metric.p50,
                absolute_delta=delta,
                relative_delta_percent=relative,
            )
        )
    return BenchmarkComparison(
        schema="flopbench-benchmark-comparison-v1",
        compatible=True,
        reason_codes=[],
        left_digest=left.digest.value,
        right_digest=right.digest.value,
        metrics=metrics,
    )
