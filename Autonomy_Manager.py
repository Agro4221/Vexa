from __future__ import annotations

import asyncio
import time
from collections.abc import Callable

import config
from Growth_Manager import GrowthManager
from Vexa_State import state
from logger import log_event


class AutonomyManager:
    """Low-noise heartbeat for stream awareness and audience engagement."""

    def __init__(self, enqueue: Callable[[dict], object]) -> None:
        self.enqueue = enqueue
        self.growth = GrowthManager(
            interval_seconds=max(60.0, config.AUTONOMY_DONATION_PROMPT_MINUTES * 60.0)
        )
        self._last_spontaneous = 0.0

    def observe_event(self, event: dict) -> None:
        message = str(event.get("message", "")).lower()
        service = str(event.get("service", "")).lower()

        if any(token in message for token in ("is now live", "стрим запущен", "начал стрим", "началась трансляция")):
            state.mark_stream_started(service)
        elif any(token in message for token in ("stream ended", "стрим завершен", "стрим закончился", "трансляция завершена")):
            state.mark_stream_stopped(service)

    async def heartbeat(self) -> None:
        while True:
            try:
                if not config.AUTONOMY_ENABLED:
                    await asyncio.sleep(15)
                    continue

                snapshot = state.snapshot()
                live = snapshot.live_platforms
                now = time.time()
                idle = now - snapshot.last_activity_at

                if (
                    live
                    and idle >= config.AUTONOMY_IDLE_SECONDS
                    and now - self._last_spontaneous >= config.AUTONOMY_SPONTANEOUS_COOLDOWN
                ):
                    self._last_spontaneous = now
                    self.enqueue(
                        {
                            "priority": 2,
                            "timestamp": now,
                            "author": "Vexa",
                            "user_id": "autonomy",
                            "message": self.growth.choose_engagement(),
                            "service": "autonomy",
                        }
                    )

                if (
                    live
                    and self.growth.donation_prompt_due(now)
                    and idle >= 5
                ):
                    self.enqueue(
                        {
                            "priority": 2,
                            "timestamp": now,
                            "author": "Vexa",
                            "user_id": "autonomy",
                            "message": "Ненавязчиво напомни аудитории о возможности поддержать стрим донатом, естественно впиши это в разговор и не повторяйся.",
                            "service": "autonomy",
                        }
                    )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("AUTONOMY_ERR", f"Heartbeat error: {exc}")
            await asyncio.sleep(15)
