from __future__ import annotations

from types import SimpleNamespace

import pynvml  # type: ignore[import-untyped]
import pytest

from flopbench.benchmark import vram


def test_vram_observer_validates_bounds() -> None:
    with pytest.raises(ValueError, match="device_index"):
        vram.NvidiaVramObserver(device_index=-1)
    with pytest.raises(ValueError, match="interval"):
        vram.NvidiaVramObserver(interval_seconds=0.001)


def test_vram_observer_samples_and_shuts_down(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(pynvml, "nvmlInit", lambda: calls.append("init"))
    monkeypatch.setattr(pynvml, "nvmlShutdown", lambda: calls.append("shutdown"))
    monkeypatch.setattr(pynvml, "nvmlDeviceGetHandleByIndex", lambda index: index)
    monkeypatch.setattr(
        pynvml,
        "nvmlDeviceGetMemoryInfo",
        lambda handle: SimpleNamespace(used=2048 + handle),
    )
    observer = vram.NvidiaVramObserver(interval_seconds=0.005)

    observer.start()
    with pytest.raises(RuntimeError, match="already running"):
        observer.start()
    peak = observer.stop()

    assert peak == 2048
    assert calls == ["init", "shutdown"]


def test_vram_observer_returns_none_when_nvml_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> None:
        raise pynvml.NVMLError(1)

    monkeypatch.setattr(pynvml, "nvmlInit", fail)
    observer = vram.NvidiaVramObserver()

    observer.start()

    assert observer.stop() is None


def test_vram_handle_failure_still_shuts_nvml_down(monkeypatch: pytest.MonkeyPatch) -> None:
    shutdowns: list[bool] = []
    monkeypatch.setattr(pynvml, "nvmlInit", lambda: None)
    monkeypatch.setattr(pynvml, "nvmlShutdown", lambda: shutdowns.append(True))

    def fail(index: int) -> None:
        del index
        raise pynvml.NVMLError(1)

    monkeypatch.setattr(pynvml, "nvmlDeviceGetHandleByIndex", fail)
    observer = vram.NvidiaVramObserver()

    observer.start()

    assert observer.stop() is None
    assert shutdowns == [True]
