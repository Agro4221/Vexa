from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import config
from Sensitive_Data_Filter import sanitize_text

_LOCK = threading.Lock()
_JSONL_PATH = config.LOG_DIR / "dialog_full.jsonl"
_TEXT_PATH = config.LOG_DIR / "dialog_full.txt"


def log_dialog(
    *,
    platform: str,
    author: str,
    author_id: str,
    message: str,
    response: str,
    emotion: str,
    moderation: dict | None = None,
) -> None:
    safe_message = sanitize_text(message)
    safe_response = sanitize_text(response)
    record = {
        "timestamp": time.time(),
        "platform": platform,
        "author": sanitize_text(author),
        "author_id": sanitize_text(author_id),
        "message": safe_message,
        "response": safe_response,
        "emotion": emotion,
        "moderation": moderation or {"action": "none", "target": ""},
    }
    nl = chr(10)
    json_line = json.dumps(
        record,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + nl
    human = nl.join(
        [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}]",
            f"Платформа: {record['platform']}",
            f"Ник: {record['author']}",
            f"ID: {record['author_id']}",
            f"Сообщение: {safe_message}",
            f"Ответ Vexa: {safe_response}",
            f"Эмоция: {emotion}",
            f"Модерация: {json.dumps(record['moderation'], ensure_ascii=False)}",
            "=" * 80,
            "",
        ]
    )
    with _LOCK:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        with _JSONL_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json_line)
        with _TEXT_PATH.open("a", encoding="utf-8") as handle:
            handle.write(human)


def jsonl_path() -> Path:
    return _JSONL_PATH


def text_path() -> Path:
    return _TEXT_PATH