from __future__ import annotations

from collections import deque
from collections.abc import Callable

import config
from logger import log_event
from social import post_to_telegram


class AnnouncementManager:
    def __init__(self, bot_provider: Callable[[], object | None] | None = None) -> None:
        self.bot_provider = bot_provider
        self._seen: set[str] = set()
        self._order = deque(maxlen=500)

    @staticmethod
    def is_start_event(event: dict) -> bool:
        message = str(event.get("message", "")).lower()
        service = str(event.get("service", "")).lower()
        return (
            "is now live" in message
            or "стрим запущен" in message
            or "начал стрим" in message
            or "началась трансляция" in message
            or (service == "vkvideolive" and "запущен" in message)
        )

    async def handle_event(self, event: dict) -> None:
        if not self.is_start_event(event):
            return
        service = str(event.get("service", "unknown")).lower()
        key = f"{service}:{str(event.get('message', ''))[:240]}"
        if key in self._seen:
            return
        self._seen.add(key)
        self._order.append(key)

        text = f"Стрим начался! {str(event.get('message', '')).strip()}"[:900]
        try:
            await post_to_telegram(text)
        except Exception as exc:
            log_event("SOCIAL_ERR", f"Анонс Telegram не отправлен: {exc}")
        await self._post_discord(text)

    async def _post_discord(self, text: str) -> None:
        if not config.DISCORD_ANNOUNCE_CHANNEL_ID or self.bot_provider is None:
            return
        bot = self.bot_provider()
        if bot is None:
            return
        try:
            channel = bot.get_channel(int(config.DISCORD_ANNOUNCE_CHANNEL_ID))
            if channel is not None:
                await channel.send(text)
                log_event("SOCIAL", "Анонс стрима отправлен в Discord.")
        except Exception as exc:
            log_event("SOCIAL_ERR", f"Анонс Discord не отправлен: {exc}")
