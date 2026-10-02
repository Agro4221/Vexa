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
    live_platforms: tuple[str, ...]
    donation_count: int


class VexaState:
    """Thread-safe runtime state shared by independent Vexa modules."""

    _RUDE_MARKERS = (
        "бля",
        "сука",
        "нахуй",
        "пизд",
        "еб",
        "мраз",
        "идиот",
        "туп",
        "дебил",
    )
    _POSITIVE_MARKERS = (
        "спасибо",
        "люблю",
        "кайф",
        "топ",
        "класс",
        "ахуенно",
        "огонь",
        "прекрасно",
    )

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mood = 50
        self._last_vision_description = "Пока ничего не вижу."
        self._last_vision_path = ""
        self._last_platform = ""
        self._last_author = ""
        self._last_activity_at = time.time()
        self._live_platforms: set[str] = set()
        self._donation_count = 0

    @property
    def mood(self) -> int:
        with self._lock:
            self._decay_mood_locked()
            return self._mood

    def change_mood(self, delta: int) -> int:
        with self._lock:
            self._decay_mood_locked()
            self._mood = max(
                config.MOOD_MIN,
                min(config.MOOD_MAX, self._mood + int(delta)),
            )
            self._last_activity_at = time.time()
            return self._mood

    def apply_chat_signal(self, message: str) -> int:
        """Adjust mood gently from chat tone without letting one message dominate."""
        text = str(message).lower()
        rude = sum(1 for marker in self._RUDE_MARKERS if marker in text)
        positive = sum(1 for marker in self._POSITIVE_MARKERS if marker in text)
        delta = max(-5, min(4, positive - rude))
        return self.change_mood(delta) if delta else self.mood

    def mark_donation(self) -> int:
        with self._lock:
            self._decay_mood_locked()
            self._donation_count += 1
            self._mood = min(config.MOOD_MAX, self._mood + 10)
            self._last_activity_at = time.time()
            return self._donation_count

    def set_vision(self, description: str, path: str = "") -> None:
        with self._lock:
            if description:
                self._last_vision_description = description.strip()
            if path:
                self._last_vision_path = str(path)

    def mark_activity(self, platform: str, author: str) -> None:
        with self._lock:
            self._last_platform = platform
            self._last_author = author
            self._last_activity_at = time.time()

    def mark_stream_started(self, platform: str) -> None:
        if not platform:
            return
        with self._lock:
            self._live_platforms.add(platform)

    def mark_stream_stopped(self, platform: str) -> None:
        if not platform:
            return
        with self._lock:
            self._live_platforms.discard(platform)

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
                live_platforms=tuple(sorted(self._live_platforms)),
                donation_count=self._donation_count,
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
