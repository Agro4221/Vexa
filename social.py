from __future__

from html import escape

import aiohttp

import config
from logger import log_event


async def post_to_telegram(text: str, chat_id: str | None = None) -> bool:
    """Send a message through Telegram Bot API when configured."""
    if not text or not config.SOCIAL_TELEGRAM_ENABLED:
        log_event("SOCIAL", "Telegram Bot API отправка отключена.")
        return False

    target = str(chat_id or config.TG_BOT_CHAT_ID)
    url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target,
        "text": escape(text),
        "parse_mode": "HTML",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload) as response:
                if response.status >= 300:
                    body = await response.text()
                    log_event("SOCIAL_ERR", f"Telegram Bot API HTTP {response.status}: {body[:300]}")
                    return False
                log_event("SOCIAL", "Сообщение в Telegram отправлено.")
                return True
    except Exception as exc:
        log_event("SOCIAL_ERR", f"Ошибка Telegram Bot API: {exc}")
        return False
