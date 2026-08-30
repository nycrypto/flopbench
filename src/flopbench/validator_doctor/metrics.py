"""Small deterministic statistics used by active tests."""

from __future__ import annotations

from itertools import pairwise
from math import ceil


def nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        raise ValueError("at least one sample is required")
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in (0, 100]")
    ordered = sorted(values)
    rank = ceil(percentile / 100 * len(ordered))
    return ordered[rank - 1]


def jitter_samples(latencies_ms: list[float]) -> list[float]:
    return [abs(current - previous) for previous, current in pairwise(latencies_ms)]
