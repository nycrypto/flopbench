"""GPU provider protocol and passive implementations."""

from __future__ import annotations

from contextlib import suppress
from importlib import import_module
from typing import Any, Protocol

from flopbench.probe.models import GpuDevice, GpuProbe, GpuStatus


class GpuProvider(Protocol):
    """Provider boundary; outputs are revalidated by the probe service."""

    name: str

    def probe(self) -> object:
        """Return an object compatible with :class:`GpuProbe`."""


def _text(value: str | bytes) -> str:
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


class NvidiaProvider:
    """Read NVIDIA GPU identity and total VRAM through NVML without workload."""

    name = "nvidia-nvml"

    def __init__(self, module: Any | None = None) -> None:
        self._module = module

    def probe(self) -> GpuProbe:
        try:
            nvml = self._module or import_module("pynvml")
        except ImportError:
            return GpuProbe(
                provider=self.name,
                status=GpuStatus.UNSUPPORTED,
                devices=[],
                reason_codes=["nvidia_binding_unavailable"],
            )

        initialized = False
        try:
            nvml.nvmlInit()
            initialized = True
            count = int(nvml.nvmlDeviceGetCount())
            if count == 0:
                return GpuProbe(
                    provider=self.name,
                    status=GpuStatus.NO_SUPPORTED_GPU,
                    devices=[],
                    reason_codes=["no_nvidia_device"],
                )

            driver_version = _text(nvml.nvmlSystemGetDriverVersion())
            devices = []
            for index in range(count):
                handle = nvml.nvmlDeviceGetHandleByIndex(index)
                memory = nvml.nvmlDeviceGetMemoryInfo(handle)
                devices.append(
                    GpuDevice(
                        vendor="NVIDIA",
                        name=_text(nvml.nvmlDeviceGetName(handle)),
                        vram_total_bytes=int(memory.total),
                        driver_version=driver_version,
                    )
                )
            return GpuProbe(
                provider=self.name,
                status=GpuStatus.DETECTED,
                devices=devices,
                reason_codes=[],
            )
        except Exception:  # NVML exposes driver-specific exception subclasses.
            return GpuProbe(
                provider=self.name,
                status=GpuStatus.UNKNOWN,
                devices=[],
                reason_codes=["nvidia_nvml_unavailable"],
            )
        finally:
            if initialized:
                with suppress(Exception):
                    nvml.nvmlShutdown()


class SafeFallbackProvider:
    """Safe result when no supported live provider can identify a GPU."""

    name = "safe-fallback"

    def probe(self) -> GpuProbe:
        return GpuProbe(
            provider=self.name,
            status=GpuStatus.NO_SUPPORTED_GPU,
            devices=[],
            reason_codes=["no_supported_gpu_provider"],
        )
