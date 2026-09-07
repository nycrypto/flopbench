"""Benchmark adapter protocol and deterministic CI implementation."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from threading import Event
from typing import Protocol

from flopbench.benchmark.models import BenchmarkAdapterIdentity, BenchmarkModelIdentity


@dataclass(frozen=True)
class AdapterRequest:
    prompt: str
    max_tokens: int
    seed: int
    timeout_seconds: float


@dataclass(frozen=True)
class AdapterSample:
    ttft_seconds: float
    latency_seconds: float
    generated_tokens: int | None
    tokens_per_second: float | None
    raw_response: bytes


class AdapterError(RuntimeError):
    code = "benchmark.adapter_error"

    def __init__(self, message: str, sample: AdapterSample | None = None) -> None:
        super().__init__(message)
        self.sample = sample


class AdapterTimeoutError(AdapterError):
    code = "benchmark.timeout"


class AdapterCancelledError(AdapterError):
    code = "benchmark.cancelled"


class AdapterPartialError(AdapterError):
    code = "benchmark.partial"
    sample: AdapterSample

    def __init__(self, sample: AdapterSample) -> None:
        super().__init__("Adapter stream ended after partial output", sample)
        self.sample = sample


class BenchmarkAdapter(Protocol):
    identity: BenchmarkAdapterIdentity

    def model_identity(self, model: str) -> BenchmarkModelIdentity: ...

    def run(self, request: AdapterRequest, cancel: Event) -> AdapterSample: ...

    def close(self) -> None: ...


class DeterministicMockAdapter:
    """No-network adapter with stable metrics for cross-platform CI."""

    identity = BenchmarkAdapterIdentity(name="mock", runtime_version="1.0.0", endpoint_scope="none")

    def __init__(self, samples: list[AdapterSample] | None = None) -> None:
        self._samples = samples or []
        self._index = 0
        self.closed = False

    def model_identity(self, model: str) -> BenchmarkModelIdentity:
        return BenchmarkModelIdentity(name=model, digest=sha256(model.encode()).hexdigest())

    def run(self, request: AdapterRequest, cancel: Event) -> AdapterSample:
        if cancel.is_set():
            raise AdapterCancelledError("Benchmark cancelled")
        if self._samples:
            sample = self._samples[self._index % len(self._samples)]
        else:
            step = self._index + 1
            generated_tokens = min(request.max_tokens, 16 + step)
            latency = (40 + step) / 100
            sample = AdapterSample(
                ttft_seconds=(50 + step) / 1000,
                latency_seconds=latency,
                generated_tokens=generated_tokens,
                tokens_per_second=generated_tokens / latency,
                raw_response=f"mock:{request.seed}:{self._index}".encode(),
            )
        self._index += 1
        return sample

    def close(self) -> None:
        self.closed = True
