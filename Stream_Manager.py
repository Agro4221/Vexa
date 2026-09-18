from __future__ import annotations

import asyncio

import config
from Twitch_Module import twitch_client
from YouTube_Module import youtube_client
from VK_Module import vk_client
from logger import log_event


class StreamManager:
    """Facade for platform-specific stream and chat operations."""

    async def start_chat_listeners(self, event_callback) -> None:
        twitch_client.event_callback = event_callback
        youtube_client.event_callback = event_callback
        tasks = []
        if config.TWITCH_ENABLED:
            tasks.append(asyncio.create_task(twitch_client.connect(), name="vexa:twitch"))
        if config.YT_ENABLED:
            tasks.append(asyncio.create_task(youtube_client.run(), name="vexa:youtube"))
        if tasks:
            await asyncio.gather(*tasks)

    async def send_twitch_message(self, message: str) -> bool:
        return await twitch_client.send_message(message)

    async def send_youtube_message(self, message: str) -> bool:
        return await youtube_client.send_message(message)

    def update_twitch(self, title: str, category_name: str | None = None) -> bool:
        from Stream_Manager_Twitch import update_twitch_channel
        return update_twitch_channel(title, category_name)

    async def update_youtube(self, video_id: str, title: str) -> bool:
        return await asyncio.to_thread(youtube_client.update_broadcast_title_sync, video_id, title)

    def vk_moderate(self, user_id: str, action: str = "ban") -> bool:
        return vk_client.moderate(user_id, action)

    async def create_global_poll(self, question: str, options: list[str]) -> dict:
        payload = {"question": question, "options": list(options)}
        log_event("STREAM", f"Global poll plan prepared: {payload}")
        return payload


stream_manager = StreamManager()
