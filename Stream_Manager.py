from __future__ import annotations

import asyncio

from Twitch_Module import twitch_client
from YouTube_Module import youtube_client
from VK_Module import vk_client
from logger import log_event


class StreamManager:
    """Facade that keeps platform implementations isolated from the core."""

    async def send_twitch_message(self, message: str) -> bool:
        return await twitch_client.send_message(message)

    async def send_youtube_message(self, message: str) -> bool:
        return await youtube_client.send_message(message)

    async def send_vk_message(self, message: str) -> bool:
        return await asyncio.to_thread(vk_client.send_message, message)

    def update_twitch(
        self,
        title: str,
        category_name: str | None = None,
    ) -> bool:
        from Stream_Manager_Twitch import update_twitch_channel

        return update_twitch_channel(title, category_name)

    async def update_youtube(
        self,
        video_id: str,
        title: str,
    ) -> bool:
        return await asyncio.to_thread(
            youtube_client.update_broadcast_title_sync,
            video_id,
            title,
        )

    def vk_moderate(
        self,
        user_id: str,
        action: str = "ban",
        duration_seconds: int | None = None,
    ) -> bool:
        return vk_client.moderate(user_id, action, duration_seconds)

    async def create_global_poll(
        self,
        question: str,
        options: list[str],
    ) -> dict:
        payload = {
            "question": question,
            "options": list(options)[:4],
        }
        log_event(
            "STREAM",
            f"Global poll plan prepared: {payload}",
        )
        return payload


stream_manager = StreamManager()
