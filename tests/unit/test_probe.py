# ruff: noqa: N802 - NVML's public API is camelCase and the fake mirrors it.

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from flopbench.cli import app
from flopbench.contracts import PrivacyLevel
from flopbench.probe.models import GpuProbe, GpuStatus, MemoryInfo
from flopbench.probe.providers import NvidiaProvider, SafeFallbackProvider
from flopbench.probe.service import (
    ProbeError,
    ProbeErrorCode,
    canonical_probe_json,
    run_fixture_probe,
    run_live_probe,
)

ROOT = Path(__file__).resolve().parents[2]
HARDWARE = ROOT / "fixtures" / "hardware"


class FakeNvml:
    def __init__(
        self, *, count: int = 1, fail_init: bool = False, fail_shutdown: bool = False
    ) -> None:
        self.count = count
        self.fail_init = fail_init
        self.fail_shutdown = fail_shutdown
        self.shutdown_calls = 0

    def nvmlInit(self) -> None:
        if self.fail_init:
            raise RuntimeError("driver missing")

    def nvmlDeviceGetCount(self) -> int:
        return self.count

    def nvmlSystemGetDriverVersion(self) -> bytes:
        return b"fixture-driver"

    def nvmlDeviceGetHandleByIndex(self, index: int) -> int:
        return index

    def nvmlDeviceGetMemoryInfo(self, handle: int) -> SimpleNamespace:
        return SimpleNamespace(total=8 * 1024**3)

    def nvmlDeviceGetName(self, handle: int) -> str:
        return "Fixture NVIDIA"

    def nvmlShutdown(self) -> None:
        self.shutdown_calls += 1
        if self.fail_shutdown:
            raise RuntimeError("shutdown failed")


def test_nvidia_provider_normalizes_vram_and_shuts_down() -> None:
    nvml = FakeNvml()

    result = NvidiaProvider(nvml).probe()

    assert result.status is GpuStatus.DETECTED
    assert result.devices[0].vram_total_bytes == 8 * 1024**3
    assert result.devices[0].driver_version == "fixture-driver"
    assert nvml.shutdown_calls == 1


def test_nvidia_provider_handles_no_devices() -> None:
    nvml = FakeNvml(count=0)

    result = NvidiaProvider(nvml).probe()

    assert result.status is GpuStatus.NO_SUPPORTED_GPU
    assert result.reason_codes == ["no_nvidia_device"]
    assert nvml.shutdown_calls == 1


@pytest.mark.parametrize("fail_shutdown", [False, True])
def test_nvidia_provider_handles_missing_driver(fail_shutdown: bool) -> None:
    nvml = FakeNvml(fail_init=True, fail_shutdown=fail_shutdown)

    result = NvidiaProvider(nvml).probe()

    assert result.status is GpuStatus.UNKNOWN
    assert result.reason_codes == ["nvidia_nvml_unavailable"]
    assert nvml.shutdown_calls == 0


def test_nvidia_provider_ignores_shutdown_failure() -> None:
    nvml = FakeNvml(fail_shutdown=True)

    result = NvidiaProvider(nvml).probe()

    assert result.status is GpuStatus.DETECTED
    assert nvml.shutdown_calls == 1


def test_safe_fallback_is_explicit() -> None:
    result = SafeFallbackProvider().probe()

    assert result.status is GpuStatus.NO_SUPPORTED_GPU
    assert result.provider == "safe-fallback"


def test_memory_rejects_available_greater_than_total() -> None:
    with pytest.raises(ValidationError, match="available_bytes"):
        MemoryInfo(total_bytes=1, available_bytes=2)


def test_gpu_status_requires_consistent_devices() -> None:
    with pytest.raises(ValidationError, match="at least one device"):
        GpuProbe(provider="bad", status=GpuStatus.DETECTED, devices=[], reason_codes=[])


def test_fixture_errors_are_safe(tmp_path: Path) -> None:
    missing = tmp_path / "SECRET-FIXTURE.json"
    with pytest.raises(ProbeError) as caught:
        run_fixture_probe(missing, PrivacyLevel.PRIVATE)
    assert caught.value.code is ProbeErrorCode.FIXTURE_READ_ERROR
    assert "SECRET-FIXTURE" not in str(caught.value)

    oversized = tmp_path / "oversized.json"
    oversized.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ProbeError) as caught:
        run_fixture_probe(oversized, PrivacyLevel.PRIVATE)
    assert caught.value.code is ProbeErrorCode.FIXTURE_TOO_LARGE

    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}", encoding="utf-8")
    with pytest.raises(ProbeError) as caught:
        run_fixture_probe(invalid, PrivacyLevel.PRIVATE)
    assert caught.value.code is ProbeErrorCode.FIXTURE_INVALID


def test_cli_outputs_deterministic_json() -> None:
    fixture = HARDWARE / "cpu-only.json"
    runner = CliRunner()

    first = runner.invoke(app, ["probe", "--fixture", str(fixture), "--format", "json"])
    second = runner.invoke(app, ["probe", "--fixture", str(fixture), "--format", "json"])

    assert first.exit_code == second.exit_code == 0
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["gpu"]["status"] == "no-supported-gpu"


def test_cli_returns_safe_nonzero_error_for_malformed_provider() -> None:
    fixture = HARDWARE / "malformed-provider-output.json"

    result = CliRunner().invoke(app, ["probe", "--fixture", str(fixture)])

    assert result.exit_code == 2
    assert result.stdout == ""
    assert json.loads(result.stderr)["code"] == "probe.provider_malformed"


def test_live_probe_produces_private_and_public_reports() -> None:
    private = run_live_probe(PrivacyLevel.PRIVATE, SafeFallbackProvider())
    public = run_live_probe(PrivacyLevel.PUBLIC, SafeFallbackProvider())

    assert private.system.host is not None
    assert public.system.host is None
    assert public.privacy_level is PrivacyLevel.PUBLIC
    assert json.loads(canonical_probe_json(public))["privacy_level"] == "public"
