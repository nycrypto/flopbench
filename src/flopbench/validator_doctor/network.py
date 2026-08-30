"""Bounded TCP-connect latency, jitter, and packet-loss adapter."""

from __future__ import annotations

import socket
import time
from typing import Protocol

from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.metrics import jitter_samples, nearest_rank
from flopbench.validator_doctor.models import NetworkTarget, NetworkTestResult, TestLimits


class NetworkAdapter(Protocol):
    def sample(self, target: NetworkTarget, timeout_seconds: float) -> float | None:
        """Return TCP connection latency in milliseconds, or None on failure."""


class TcpConnectAdapter:
    """Open and close one TCP connection without sending application payload."""

    def sample(self, target: NetworkTarget, timeout_seconds: float) -> float | None:
        started = time.perf_counter()
        try:
            with socket.create_connection((target.host, target.port), timeout=timeout_seconds):
                return (time.perf_counter() - started) * 1000
        except OSError:
            return None


def run_network_test(
    target: NetworkTarget,
    limits: TestLimits,
    *,
    adapter: NetworkAdapter | None = None,
) -> NetworkTestResult:
    sampler = adapter or TcpConnectAdapter()
    samples = [
        sampler.sample(target, limits.network_timeout_seconds)
        for _ in range(limits.network_attempts)
    ]
    successful = [sample for sample in samples if sample is not None]
    received = len(successful)
    if not successful:
        return NetworkTestResult(
            status=ResultStatus.UNKNOWN,
            target=target.display,
            attempts=limits.network_attempts,
            received=0,
            packet_loss_percent=100.0,
            latency_p50_ms=None,
            latency_p95_ms=None,
            jitter_p95_ms=None,
            reason_codes=["doctor.network.target_unreachable"],
        )

    packet_loss = (limits.network_attempts - received) / limits.network_attempts * 100
    jitters = jitter_samples(successful)
    jitter_p95 = nearest_rank(jitters, 95) if jitters else 0.0
    latency_p50 = nearest_rank(successful, 50)
    latency_p95 = nearest_rank(successful, 95)
    if packet_loss >= 50:
        status = ResultStatus.FAIL
        reason = "doctor.network.packet_loss_high"
    elif packet_loss > 0 or jitter_p95 > 50:
        status = ResultStatus.WARN
        reason = "doctor.network.jitter_or_loss_detected"
    else:
        status = ResultStatus.PASS
        reason = "doctor.network.connection_stable"
    return NetworkTestResult(
        status=status,
        target=target.display,
        attempts=limits.network_attempts,
        received=received,
        packet_loss_percent=packet_loss,
        latency_p50_ms=latency_p50,
        latency_p95_ms=latency_p95,
        jitter_p95_ms=jitter_p95,
        reason_codes=[reason],
    )
