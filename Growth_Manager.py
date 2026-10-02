from __future__ import annotations

import random
import time

from logger import log_event


class GrowthManager:
    """Keeps engagement and donation prompting separate from the LLM core."""

    def __init__(self, interval_seconds: float = 1800.0) -> None:
        self.interval_seconds = max(60.0, interval_seconds)
        self._last_prompt = 0.0

    def donation_prompt_due(self, now: float | None = None) -> bool:
        current = now or time.time()
        if current - self._last_prompt < self.interval_seconds:
            return False
        self._last_prompt = current
        return True

    def choose_engagement(self) -> str:
        choices = (
            "Расспроси аудиторию о том, что им сейчас интереснее всего.",
            "Подхвати живую тему из чата и вовлеки в неё нескольких зрителей.",
            "Напомни, что поддержать стрим можно донатом, естественно вписав это в разговор.",
        )
        return random.choice(choices)

    def log_growth_event(self, message: str) -> None:
        log_event("GROWTH", message)
