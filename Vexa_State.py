from __future__ import annotations

import threading
import time
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class VexaStateSnapshot:
    mood: int
    last_vision_description: str
    last_vision_path: str
    last_platform: str
    last_author: str
    last_activity_at: float


class VexaState:
    """Thread-safe runtime state shared by modules without coupling them together."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mood = 50
        self._last_vision_description = "Пока ничего не вижу."
        self._last_vision_path = ""
        self._last_platform = ""
        self._last_author = ""
        self._last_activity_at = time.time()

    @property
    def mood(self) -> int:
        with self._lock:
            self._decay_mood_locked()
            return self._mood

    def change_mood(self, delta: int) -> int:
        with self._lock:
            self._decay_mood_locked()
            self._mood = max(config.MOOD_MIN, min(config.MOOD_MAX, self._mood + int(delta)))
            self._last_activity_at = time.time()
            return self._mood

    def set_vision(self, description: str, path: str = "") -> None:
        with self._lock:
            if description:
                self._last_vision_description = description.strip()
            if path:
                self._last_vision_path = str(path)
            self._last_activity_at = time.time()

    def mark_activity(self, platform: str, author: str) -> None:
        with self._lock:
            self._last_platform = platform
            self._last_author = author
            self._last_activity_at = time.time()

    def snapshot(self) -> VexaStateSnapshot:
        with self._lock:
            self._decay_mood_locked()
            return VexaStateSnapshot(
                mood=self._mood,
                last_vision_description=self._last_vision_description,
                last_vision_path=self._last_vision_path,
                last_platform=self._last_platform,
                last_author=self._last_author,
                last_activity_at=self._last_activity_at,
            )

    def _decay_mood_locked(self) -> None:
        minutes = (time.time() - self._last_activity_at) / 60.0
        if minutes <= 0 or config.MOOD_DECAY_PER_MINUTE <= 0:
            return
        step = int(minutes * config.MOOD_DECAY_PER_MINUTE)
        if step <= 0:
            return
        target = 50
        if self._mood > target:
            self._mood = max(target, self._mood - step)
        elif self._mood < target:
            self._mood = min(target, self._mood + step)
        self._last_activity_at = time.time()


state = VexaState()
