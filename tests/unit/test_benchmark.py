from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from threading import Event
from uuid import UUID

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from flopbench.benchmark.adapters import (
    AdapterCancelledError,
    AdapterPartialError,
    AdapterRequest,
    AdapterSample,
    AdapterTimeoutError,
    DeterministicMockAdapter,
)
from flopbench.benchmark.endpoint import EndpointError, EndpointErrorCode, validate_endpoint
from flopbench.benchmark.engine import (
    canonical_benchmark_json,
    run_benchmark,
)
from flopbench.benchmark.workload import LoadedWorkload, load_workload
from flopbench.cli import app

ROOT = Path(__file__).resolve().parents[2]
WORKLOAD = ROOT / "src" / "flopbench" / "workloads" / "smoke-v1.json"
FIXED_ID = UUID("018f4cf8-6c40-7b29-9c61-5c120cd9a005")
FIXED_TIME = datetime(2026, 9, 7, 12, 0, tzinfo=UTC)


def _sample(ttft: float, latency: float, tokens: int = 10) -> AdapterSample:
    return AdapterSample(ttft, latency, tokens, tokens / latency, f"{ttft}:{latency}".encode())


def _workload(*, warmups: int = 1, measured: int = 3) -> LoadedWorkload:
    loaded = load_workload(WORKLOAD)
    definition = loaded.definition.model_copy(
        update={"warmup_runs": warmups, "measured_runs": measured}
    )
    return LoadedWorkload(
        definition=definition, sha256=loaded.sha256, byte_length=loaded.byte_length
    )


def test_s5_t01_deterministic_mock_has_fixed_metrics() -> None:
    adapter = DeterministicMockAdapter()

    report = run_benchmark(
        adapter,
        _workload(warmups=0, measured=3),
        "fixture-model",
        benchmark_id=FIXED_ID,
        now=lambda: FIXED_TIME,
    )

    assert report.benchmark_id == FIXED_ID
    assert report.metrics.ttft.samples == [0.051, 0.052, 0.053]
    assert report.metrics.latency.samples == [0.41, 0.42, 0.43]
    assert report.outcomes.success == 3
    assert report.outcomes.error_rate == 0
    assert report.metrics.ttft.confidence == "simulated"
    assert report.metrics.tokens_per_second.confidence == "simulated"
    assert adapter.closed


def test_s5_t02_warmup_is_recorded_but_excluded_from_metrics() -> None:
    adapter = DeterministicMockAdapter([_sample(9, 9), _sample(1, 1), _sample(2, 2), _sample(3, 3)])

    report = run_benchmark(adapter, _workload(), "fixture", now=lambda: FIXED_TIME)

    assert len(report.runs) == 4
    assert report.runs[0].warmup is True
    assert report.metrics.latency.samples == [1.0, 2.0, 3.0]


def test_s5_t03_nearest_rank_p50_and_p95_are_correct() -> None:
    adapter = DeterministicMockAdapter([_sample(0.3, 3), _sample(0.1, 1), _sample(0.2, 2)])

    report = run_benchmark(adapter, _workload(warmups=0), "fixture", now=lambda: FIXED_TIME)

    assert report.metrics.latency.p50 == 2
    assert report.metrics.latency.p95 == 3
    assert report.metrics.ttft.p50 == 0.2
    assert report.metrics.ttft.p95 == 0.3


class _ScriptedAdapter(DeterministicMockAdapter):
    def __init__(self, actions: list[AdapterSample | BaseException]) -> None:
        super().__init__()
        self.actions = actions
        self.position = 0

    def run(self, request: AdapterRequest, cancel: Event) -> AdapterSample:
        del request, cancel
        action = self.actions[self.position]
        self.position += 1
        if isinstance(action, BaseException):
            raise action
        return action


def test_s5_t04_timeout_is_included_in_error_rate() -> None:
    adapter = _ScriptedAdapter([_sample(0.1, 1), AdapterTimeoutError("slow"), _sample(0.3, 3)])

    report = run_benchmark(adapter, _workload(warmups=0), "fixture", now=lambda: FIXED_TIME)

    assert report.outcomes.timeout == 1
    assert report.outcomes.error_rate == pytest.approx(1 / 3)
    assert len(report.metrics.latency.samples) == 2


def test_s5_t05_interrupted_stream_is_explicitly_partial() -> None:
    partial = _sample(0.1, 0.5, 4)
    adapter = _ScriptedAdapter([AdapterPartialError(partial), _sample(0.2, 1), _sample(0.3, 2)])

    report = run_benchmark(adapter, _workload(warmups=0), "fixture", now=lambda: FIXED_TIME)

    assert report.runs[0].outcome == "partial"
    assert report.runs[0].generated_tokens == 4
    assert report.runs[0].error_code == "benchmark.partial"
    assert report.outcomes.partial == 1
    assert report.outcomes.error_rate == pytest.approx(1 / 3)


@pytest.mark.parametrize("value", [-1.0, float("nan")])
def test_s5_t06_negative_or_nan_duration_is_rejected(value: float) -> None:
    adapter = DeterministicMockAdapter([_sample(value, 1)])

    with pytest.raises(ValidationError):
        run_benchmark(adapter, _workload(warmups=0, measured=1), "fixture", now=lambda: FIXED_TIME)

    assert adapter.closed


def test_s5_t07_prompt_change_changes_raw_workload_digest(tmp_path: Path) -> None:
    original = load_workload(WORKLOAD)
    changed = tmp_path / "changed.json"
    changed.write_bytes(WORKLOAD.read_bytes().replace(b"deterministic", b"repeatable", 1))

    assert load_workload(changed).sha256 != original.sha256


def test_s5_t08_same_fixture_has_byte_identical_canonical_report() -> None:
    def one_run() -> str:
        report = run_benchmark(
            DeterministicMockAdapter(),
            _workload(),
            "fixture-model",
            benchmark_id=FIXED_ID,
            now=lambda: FIXED_TIME,
        )
        return canonical_benchmark_json(report)

    assert one_run() == one_run()


def test_s5_t09_cancellation_always_closes_adapter() -> None:
    adapter = _ScriptedAdapter([_sample(0.1, 1), AdapterCancelledError("cancel")])
    report = run_benchmark(adapter, _workload(warmups=0), "fixture", now=lambda: FIXED_TIME)

    assert adapter.closed
    assert report.outcomes.success == 1
    assert report.outcomes.cancelled == 2
    assert report.outcomes.error_rate == pytest.approx(2 / 3)
    assert report.runs[-1].error_code == "benchmark.cancelled_before_start"
    assert adapter.position == 2


def test_keyboard_interrupt_preserves_completed_runs_and_cleans_observer() -> None:
    adapter = _ScriptedAdapter([_sample(0.1, 1), KeyboardInterrupt()])
    observer = _FakeVramObserver()
    report = run_benchmark(
        adapter,
        _workload(warmups=0),
        "fixture",
        vram_observer=observer,
    )
    assert adapter.closed
    assert observer.starts == observer.stops == 2
    assert report.outcomes.success == 1
    assert report.outcomes.cancelled == 2


class _FakeVramObserver:
    def __init__(self) -> None:
        self.starts = 0
        self.stops = 0

    def start(self) -> None:
        self.starts += 1

    def stop(self) -> int:
        self.stops += 1
        return 1024 * self.stops


def test_peak_vram_observer_is_bounded_to_each_run() -> None:
    observer = _FakeVramObserver()

    report = run_benchmark(
        DeterministicMockAdapter(),
        _workload(warmups=1, measured=2),
        "fixture",
        now=lambda: FIXED_TIME,
        vram_observer=observer,
    )

    assert observer.starts == observer.stops == 3
    assert report.metrics.peak_vram.samples == [2048.0, 3072.0]


def test_s5_t10_external_endpoint_outside_allowlist_is_rejected() -> None:
    with pytest.raises(EndpointError) as caught:
        validate_endpoint("https://203.0.113.10:443", allow_external=True, allowlist=("other",))

    assert caught.value.code is EndpointErrorCode.NOT_ALLOWED


def test_loopback_and_explicit_allowlist_policy() -> None:
    local = validate_endpoint("http://127.0.0.1:11434")
    external = validate_endpoint(
        "https://inference.example:443/v1",
        allow_external=True,
        allowlist=("inference.example",),
    )

    assert local.scope == "loopback"
    assert external.scope == "allowlisted_external"


@pytest.mark.parametrize(
    "value",
    [
        "ftp://localhost/model",
        "http://user:secret@localhost:8000",
        "http://localhost:8000/v1?token=secret",
        "http://localhost:8000/a/../b",
        "http://localhost:8000/a/%2e%2e/b",
        "http://bad host:8000",
    ],
)
def test_unsafe_endpoint_forms_are_rejected(value: str) -> None:
    with pytest.raises(EndpointError):
        validate_endpoint(value)


def test_benchmark_cli_runs_mock_and_emits_v2_json() -> None:
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run",
            "--adapter",
            "mock",
            "--model",
            "fixture-model",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["schema"] == "flopbench-benchmark-report-v2"
    assert payload["outcomes"] == {
        "cancelled": 0,
        "error": 0,
        "error_rate": 0.0,
        "partial": 0,
        "success": 3,
        "timeout": 0,
    }


def test_benchmark_cli_rejects_external_endpoint_before_network() -> None:
    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run",
            "--adapter",
            "ollama",
            "--endpoint",
            "https://203.0.113.10",
        ],
    )

    assert result.exit_code == 2
    assert "benchmark.endpoint_not_allowed" in result.stderr
