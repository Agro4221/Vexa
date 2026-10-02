from __future__ import annotations

import requests

import config
from logger import log_event


class VKPlayClient:
    """Configurable VK Video Live adapter. No undocumented endpoint is assumed."""

    def __init__(self) -> None:
        self.service_key = config.VK_SERVICE_KEY
        self.protected_key = config.VK_PROTECTED_KEY
        self.base_url = config.VK_API_BASE_URL.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(
            config.VK_ENABLED
            and self.service_key
            and self.base_url
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.service_key}",
            "Content-Type": "application/json",
        }
        if self.protected_key:
            headers["X-Protected-Key"] = self.protected_key
        return headers

    def _url(self, configured_path: str, **values) -> str:
        path = configured_path.format(**values).lstrip("/")
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not self.base_url:
            raise RuntimeError("VK_API_BASE_URL не задан")
        return f"{self.base_url}/{path}"

    def moderate(
        self,
        user_id: str,
        action: str = "ban",
        duration_seconds: int | None = None,
    ) -> bool:
        if not self.enabled or not config.VK_MODERATION_PATH:
            log_event(
                "VK",
                "VK moderation недоступна: VK_API_BASE_URL/VK_MODERATION_PATH не настроены.",
            )
            return False
        payload = {
            "user_id": str(user_id),
            "action": action,
            "duration_seconds": duration_seconds,
        }
        response = requests.post(
            self._url(
                config.VK_MODERATION_PATH,
                user_id=user_id,
                action=action,
            ),
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        log_event(
            "MODERATION",
            f"VK moderation выполнена: user={user_id}, action={action}",
        )
        return True

    def send_message(self, message: str) -> bool:
        if not message or not self.enabled or not config.VK_CHAT_SEND_PATH:
            return False
        response = requests.post(
            self._url(config.VK_CHAT_SEND_PATH),
            json={"message": message[:500]},
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return True

    def send_request(self, path: str, payload: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("VK API не настроен")
        response = requests.post(
            self._url(path),
            json=payload,
            headers=self._headers(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json() if response.content else {}


vk_client = VKPlayClient()
