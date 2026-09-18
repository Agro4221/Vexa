from __future__ import annotations

import requests

import config
from logger import log_event


class VKPlayClient:
    """Configurable VK Play Live adapter; no guessed endpoint is hard-coded."""

    def __init__(self) -> None:
        self.service_key = config.VK_SERVICE_KEY
        self.protected_key = config.VK_PROTECTED_KEY
        self.base_url = config.VK_API_BASE_URL

    @property
    def enabled(self) -> bool:
        return bool(config.VK_ENABLED and self.service_key and self.base_url)

    def moderate(self, user_id: str, action: str = "ban") -> bool:
        if not self.enabled or not config.VK_MODERATION_PATH:
            log_event("VK", "VK Play moderation недоступна: официальный endpoint не задан в конфигурации.")
            return False
        url = f"{self.base_url}/{config.VK_MODERATION_PATH.lstrip('/')}"
        payload = {"user_id": str(user_id), "action": action}
        headers = {"Authorization": f"Bearer {self.service_key}"}
        if self.protected_key:
            headers["X-Protected-Key"] = self.protected_key
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code >= 300:
            log_event("VK_ERR", f"VK moderation HTTP {response.status_code}: {response.text[:300]}")
            return False
        return True

    def send_request(self, path: str, payload: dict) -> dict:
        if not self.enabled:
            raise RuntimeError("VK Play API не настроен")
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.service_key}"}
        if self.protected_key:
            headers["X-Protected-Key"] = self.protected_key
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json() if response.content else {}


vk_client = VKPlayClient()
