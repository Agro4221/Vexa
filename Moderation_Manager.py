from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass
from typing import Any

import requests

import config
from logger import log_event


@dataclass(frozen=True)
class ModerationRequest:
    platform: str
    user_id: str
    action: str = "ban"
    duration_seconds: int | None = None
    reason: str = "AI moderation"
    message_id: str = ""


class ModerationManager:
    """Platform-specific moderation behind one audit-friendly interface."""

    def __init__(self) -> None:
        self._twitch_broadcaster_id: str | None = None
        self._twitch_lock = threading.Lock()

    async def execute(self, request: ModerationRequest) -> bool:
        if not config.ALLOW_AI_MODERATION:
            log_event("MODERATION", f"Модерация предложена, но отключена: {request}")
            return False
        platform = request.platform.lower()
        if platform == "twitch":
            return await asyncio.to_thread(self._twitch, request)
        if platform == "youtube":
            return await asyncio.to_thread(self._youtube, request)
        if platform in {"vk", "vkvideolive", "vkplay"}:
            return await asyncio.to_thread(self._vk, request)
        log_event("MODERATION", f"Неизвестная платформа: {request.platform}")
        return False

    def _twitch_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {config.TWITCH_TOKEN}",
            "Client-Id": config.TWITCH_CLIENT_ID,
            "Content-Type": "application/json",
        }

    def _twitch_broadcaster(self) -> str:
        with self._twitch_lock:
            if self._twitch_broadcaster_id:
                return self._twitch_broadcaster_id
            response = requests.get(
                "https://api.twitch.tv/helix/users",
                headers=self._twitch_headers(),
                params={"login": config.TWITCH_CHANNEL},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                raise RuntimeError("Twitch broadcaster not found")
            self._twitch_broadcaster_id = str(data[0]["id"])
            return self._twitch_broadcaster_id

    def _twitch(self, request: ModerationRequest) -> bool:
        if not config.TWITCH_ENABLED or not config.TWITCH_CLIENT_ID or not config.TWITCH_TOKEN:
            return False
        if not request.user_id:
            raise ValueError("Twitch moderation requires user_id")
        moderator_id = config.TWITCH_MODERATOR_ID or self._twitch_broadcaster()
        params = {
            "broadcaster_id": self._twitch_broadcaster(),
            "moderator_id": moderator_id,
        }
        body: dict[str, Any] = {
            "data": {
                "user_id": request.user_id,
                "reason": request.reason[:500],
            }
        }
        if request.action == "timeout":
            body["data"]["duration"] = max(
                1, min(1_209_600, int(request.duration_seconds or 300))
            )
        elif request.action != "ban":
            raise ValueError(f"Unsupported Twitch moderation action: {request.action}")
        response = requests.post(
            "https://api.twitch.tv/helix/moderation/bans",
            headers=self._twitch_headers(),
            params=params,
            json=body,
            timeout=10,
        )
        response.raise_for_status()
        log_event("MODERATION", f"Twitch {request.action}: user={request.user_id}")
        return True

    def _youtube(self, request: ModerationRequest) -> bool:
        from YouTube_Module import youtube_client

        return youtube_client.moderate_user_sync(
            user_channel_id=request.user_id,
            action=request.action,
            duration_seconds=request.duration_seconds,
            reason=request.reason,
            message_id=request.message_id,
        )

    def _vk(self, request: ModerationRequest) -> bool:
        if not config.VK_ENABLED or not config.VK_SERVICE_KEY:
            return False
        if not config.VK_API_BASE_URL or not config.VK_MODERATION_PATH:
            log_event(
                "MODERATION",
                "VK moderation endpoint не задан; отказ без выдумывания API.",
            )
            return False
        path = config.VK_MODERATION_PATH.format(
            user_id=request.user_id,
            action=request.action,
        )
        url = path if path.startswith("http") else f"{config.VK_API_BASE_URL}/{path.lstrip('/')}"
        payload: dict[str, Any] = {
            "user_id": request.user_id,
            "action": request.action,
            "duration_seconds": request.duration_seconds,
            "reason": request.reason[:500],
        }
        headers = {"Authorization": f"Bearer {config.VK_SERVICE_KEY}"}
        if config.VK_PROTECTED_KEY:
            headers["X-Protected-Key"] = config.VK_PROTECTED_KEY
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        log_event("MODERATION", f"VK moderation выполнена: user={request.user_id}")
        return True


moderation = ModerationManager()
