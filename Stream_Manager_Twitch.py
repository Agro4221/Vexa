from __future__ import annotations

import requests

import config
from logger import log_event


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.TWITCH_TOKEN}",
        "Client-Id": config.TWITCH_CLIENT_ID,
        "Content-Type": "application/json",
    }


def _broadcaster_id() -> str:
    response = requests.get(
        "https://api.twitch.tv/helix/users",
        headers=_headers(),
        params={"login": config.TWITCH_CHANNEL},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json().get("data", [])
    if not data:
        raise RuntimeError(f"Twitch channel не найден: {config.TWITCH_CHANNEL}")
    return str(data[0]["id"])


def update_twitch_channel(title: str, category_name: str | None = None) -> bool:
    if not config.TWITCH_ENABLED:
        return False
    payload = {"title": title[:140]}
    if category_name:
        response = requests.get(
            "https://api.twitch.tv/helix/search/categories",
            headers=_headers(),
            params={"query": category_name},
            timeout=10,
        )
        response.raise_for_status()
        categories = response.json().get("data", [])
        if categories:
            payload["game_id"] = str(categories[0]["id"])
    response = requests.patch(
        "https://api.twitch.tv/helix/channels",
        headers=_headers(),
        params={"broadcaster_id": _broadcaster_id()},
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    log_event("TWITCH", f"Название обновлено: {title}")
    return True
