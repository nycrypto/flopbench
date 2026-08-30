"""Small user-selected NTP clock-offset adapter with no retries."""

from __future__ import annotations

import socket
import struct
import time
from typing import Protocol

from flopbench.contracts import ResultStatus
from flopbench.validator_doctor.models import ClockTestResult

NTP_EPOCH_DELTA = 2_208_988_800


class ClockAdapter(Protocol):
    def sample(self, server: str, timeout_seconds: float) -> tuple[float, float] | None:
        """Return (offset_ms, round_trip_ms), or None when no valid reply arrives."""


def _ntp_timestamp(payload: bytes, offset: int) -> float:
    seconds, fraction = struct.unpack_from("!II", payload, offset)
    return float(seconds - NTP_EPOCH_DELTA + fraction / 2**32)


class NtpAdapter:
    def sample(self, server: str, timeout_seconds: float) -> tuple[float, float] | None:
        request = bytearray(48)
        request[0] = 0x1B
        started = time.time()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(timeout_seconds)
                client.sendto(request, (server, 123))
                payload, _address = client.recvfrom(512)
        except OSError:
            return None
        finished = time.time()
        if len(payload) < 48:
            return None
        receive_time = _ntp_timestamp(payload, 32)
        transmit_time = _ntp_timestamp(payload, 40)
        offset_ms = ((receive_time - started) + (transmit_time - finished)) / 2 * 1000
        round_trip_ms = max((finished - started) - (transmit_time - receive_time), 0) * 1000
        return offset_ms, round_trip_ms


def run_clock_test(
    server: str,
    timeout_seconds: float,
    *,
    adapter: ClockAdapter | None = None,
) -> ClockTestResult:
    sample = (adapter or NtpAdapter()).sample(server, timeout_seconds)
    if sample is None:
        return ClockTestResult(
            status=ResultStatus.UNKNOWN,
            server=server,
            offset_ms=None,
            round_trip_ms=None,
            reason_codes=["doctor.clock.source_unreachable"],
        )
    offset_ms, round_trip_ms = sample
    absolute_offset = abs(offset_ms)
    if absolute_offset > 1000:
        status = ResultStatus.FAIL
        reason = "doctor.clock.offset_exceeds_community_limit"
    elif absolute_offset > 100:
        status = ResultStatus.WARN
        reason = "doctor.clock.offset_has_low_margin"
    else:
        status = ResultStatus.PASS
        reason = "doctor.clock.offset_healthy"
    return ClockTestResult(
        status=status,
        server=server,
        offset_ms=offset_ms,
        round_trip_ms=round_trip_ms,
        reason_codes=[reason],
    )
