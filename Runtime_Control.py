from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import Callable

from logger import log_event


class GenerationCancelled(RuntimeError):
    """Raised when an operator or safety control stops the current generation."""


class RuntimeControl:
    def __init__(self) -> None:
        self._generation_stop = threading.Event()
        self._tts_stop = threading.Event()
        self._lock = threading.RLock()
        self._tts_stopper: Callable[[], object] | None = None

    def begin_generation(self) -> None:
        self._generation_stop.clear()

    def request_stop_generation(self) -> None:
        self._generation_stop.set()
        log_event("CONTROL", "Остановлена текущая генерация текста.")

    def generation_stop_requested(self) -> bool:
        return self._generation_stop.is_set()

    def raise_if_generation_stopped(self) -> None:
        if self.generation_stop_requested():
            raise GenerationCancelled("LLM generation stopped by control")

    def clear_tts_stop(self) -> None:
        self._tts_stop.clear()

    def request_stop_tts(self) -> None:
        self._tts_stop.set()
        log_event("CONTROL", "Остановлена текущая озвучка.")
        with self._lock:
            stopper = self._tts_stopper
        if stopper is not None:
            try:
                result = stopper()
                if inspect.isawaitable(result):
                    try:
                        asyncio.get_running_loop().create_task(result)
                    except RuntimeError:
                        pass
            except Exception as exc:
                log_event("CONTROL_ERR", f"Не удалось остановить TTS: {exc}")

    def tts_stop_requested(self) -> bool:
        return self._tts_stop.is_set()

    def register_tts_stopper(self, stopper: Callable[[], object] | None) -> None:
        with self._lock:
            self._tts_stopper = stopper

    def stop_all(self) -> None:
        self.request_stop_generation()
        self.request_stop_tts()


control = RuntimeControl()
