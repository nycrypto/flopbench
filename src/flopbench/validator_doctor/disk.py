"""Bounded disk throughput and latency test in an isolated temporary directory."""

from __future__ import annotations

import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.metrics import nearest_rank
from flopbench.validator_doctor.models import DiskTestResult, TestLimits

AfterChunk = Callable[[str, int, Path], None]


class DiskTestCancelledError(RuntimeError):
    """Cooperative cancellation used to prove cleanup behavior."""


def _result(
    status: ResultStatus,
    reason: str,
    *,
    bytes_tested: int = 0,
    write_bps: float | None = None,
    read_bps: float | None = None,
    write_p95: float | None = None,
    read_p95: float | None = None,
) -> DiskTestResult:
    return DiskTestResult(
        status=status,
        bytes_tested=bytes_tested,
        write_bytes_per_second=write_bps,
        read_bytes_per_second=read_bps,
        write_latency_p95_ms=write_p95,
        read_latency_p95_ms=read_p95,
        reason_codes=[reason],
    )


def run_disk_test(
    limits: TestLimits,
    *,
    temp_root: Path | None = None,
    after_chunk: AfterChunk | None = None,
) -> DiskTestResult:
    """Write and read a bounded file, always deleting the isolated directory."""

    if temp_root is not None and temp_root.is_symlink():
        return _result(ResultStatus.UNSUPPORTED, "doctor.disk.temp_root_symlink_rejected")
    try:
        with tempfile.TemporaryDirectory(prefix="flopbench-", dir=temp_root) as directory:
            work_directory = Path(directory).resolve(strict=True)
            if temp_root is not None and not work_directory.is_relative_to(temp_root.resolve()):
                return _result(ResultStatus.UNSUPPORTED, "doctor.disk.temp_boundary_invalid")
            test_file = work_directory / "disk-test.bin"
            chunk = bytes(index % 251 for index in range(limits.disk_chunk_bytes))
            write_latencies: list[float] = []
            read_latencies: list[float] = []
            started = time.perf_counter()
            written = 0
            with test_file.open("xb") as stream:
                while written < limits.disk_bytes:
                    if time.perf_counter() - started > limits.max_duration_seconds:
                        return _result(
                            ResultStatus.WARN,
                            "doctor.disk.duration_limit_reached",
                            bytes_tested=written,
                        )
                    size = min(len(chunk), limits.disk_bytes - written)
                    sample_started = time.perf_counter()
                    stream.write(chunk[:size])
                    write_latencies.append((time.perf_counter() - sample_started) * 1000)
                    written += size
                    if after_chunk is not None:
                        after_chunk("write", len(write_latencies), test_file)
                stream.flush()
                os.fsync(stream.fileno())
            write_seconds = max(time.perf_counter() - started, 1e-9)

            read_started = time.perf_counter()
            read = 0
            with test_file.open("rb") as stream:
                while read < written:
                    if time.perf_counter() - started > limits.max_duration_seconds:
                        return _result(
                            ResultStatus.WARN,
                            "doctor.disk.duration_limit_reached",
                            bytes_tested=read,
                        )
                    sample_started = time.perf_counter()
                    payload = stream.read(min(limits.disk_chunk_bytes, written - read))
                    read_latencies.append((time.perf_counter() - sample_started) * 1000)
                    if not payload:
                        return _result(ResultStatus.UNKNOWN, "doctor.disk.short_read")
                    read += len(payload)
                    if after_chunk is not None:
                        after_chunk("read", len(read_latencies), test_file)
            read_seconds = max(time.perf_counter() - read_started, 1e-9)

            write_bps = written / write_seconds
            read_bps = read / read_seconds
            write_p95 = nearest_rank(write_latencies, 95)
            read_p95 = nearest_rank(read_latencies, 95)
            slowest_bps = min(write_bps, read_bps)
            highest_latency = max(write_p95, read_p95)
            if slowest_bps < 10_000_000 or highest_latency > 200:
                status = ResultStatus.FAIL
                reason = "doctor.disk.performance_below_community_floor"
            elif slowest_bps < 50_000_000 or highest_latency > 50:
                status = ResultStatus.WARN
                reason = "doctor.disk.performance_has_low_margin"
            else:
                status = ResultStatus.PASS
                reason = "doctor.disk.performance_healthy"
            return _result(
                status,
                reason,
                bytes_tested=written,
                write_bps=write_bps,
                read_bps=read_bps,
                write_p95=write_p95,
                read_p95=read_p95,
            )
    except DiskTestCancelledError:
        raise
    except OSError:
        return _result(ResultStatus.UNSUPPORTED, "doctor.disk.temp_write_unavailable")
