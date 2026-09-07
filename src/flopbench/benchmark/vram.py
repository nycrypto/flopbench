"""Bounded NVIDIA VRAM sampling used only during benchmark requests."""

from __future__ import annotations

from contextlib import suppress
from threading import Event, Thread
from time import sleep
from typing import Protocol

import pynvml  # type: ignore[import-untyped]


class VramObserver(Protocol):
    def start(self) -> None: ...

    def stop(self) -> int | None: ...


class NvidiaVramObserver:
    """Sample total used memory on one NVIDIA device in a short-lived thread."""

    def __init__(self, *, device_index: int = 0, interval_seconds: float = 0.02) -> None:
        if device_index < 0:
            raise ValueError("device_index must be non-negative")
        if not 0.005 <= interval_seconds <= 1:
            raise ValueError("interval_seconds must be between 0.005 and 1")
        self.device_index = device_index
        self.interval_seconds = interval_seconds
        self._stop = Event()
        self._thread: Thread | None = None
        self._peak: int | None = None
        self._available = False
        self._initialized = False

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("VRAM observer is already running")
        self._stop.clear()
        self._peak = None
        try:
            pynvml.nvmlInit()
            self._initialized = True
            pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
        except pynvml.NVMLError:
            self._available = False
            if self._initialized:
                with suppress(pynvml.NVMLError):
                    pynvml.nvmlShutdown()
                self._initialized = False
            return
        self._available = True
        self._thread = Thread(target=self._sample_loop, name="flopbench-vram", daemon=True)
        self._thread.start()

    def _sample_loop(self) -> None:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
            while not self._stop.is_set():
                used = int(pynvml.nvmlDeviceGetMemoryInfo(handle).used)
                self._peak = used if self._peak is None else max(self._peak, used)
                sleep(self.interval_seconds)
        except pynvml.NVMLError:
            self._available = False

    def stop(self) -> int | None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 4))
            self._thread = None
        if self._available:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(self.device_index)
                used = int(pynvml.nvmlDeviceGetMemoryInfo(handle).used)
                self._peak = used if self._peak is None else max(self._peak, used)
            except pynvml.NVMLError:
                self._available = False
        result = self._peak if self._available else None
        if self._initialized:
            with suppress(pynvml.NVMLError):
                pynvml.nvmlShutdown()
            self._initialized = False
        return result
