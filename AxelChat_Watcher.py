from __future__ import annotations

import configparser
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from logger import log_event

_SESSION_RE = re.compile(r"(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}(?:\.\d+)?)")


class AxelChatHandler:
    def __init__(self, queue_submit: Callable[[dict[str, Any]], None], loop) -> None:
        self.queue_submit = queue_submit
        self.loop = loop
        self._last_idx_by_file: dict[str, int] = {}

    def on_created(self, event) -> None:
        if not event.is_directory:
            self.on_modified(event)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.name.lower() == "messages.ini":
            self.process_file(path)

    def initial_scan(self, root: Path, *, emit_existing: bool = False) -> None:
        for path in sorted(root.rglob("messages.ini")):
            self.process_file(path, emit_existing=emit_existing)

    def process_file(self, path: Path, *, emit_existing: bool = True) -> None:
        key = str(path.resolve())
        last_idx = self._last_idx_by_file.get(key, -1)
        parser = configparser.RawConfigParser(interpolation=None, strict=False)
        try:
            loaded = parser.read(path, encoding="utf-8")
            if not loaded:
                parser.read(path, encoding="cp1251")
        except (OSError, configparser.Error) as exc:
            log_event("CHAT_ERR", f"Не удалось прочитать {path}: {exc}")
            return

        session_id = self._session_id(path)
        rows: list[tuple[int, dict[str, str]]] = []
        for section in parser.sections():
            try:
                idx = int(section)
            except ValueError:
                continue
            if idx <= last_idx:
                continue
            rows.append(
                (
                    idx,
                    {
                        "author": parser.get(section, "author", fallback="Anon").strip(),
                        "author_id": parser.get(section, "author_id", fallback="").strip(),
                        "message": parser.get(section, "message", fallback="").strip(),
                        "time": parser.get(section, "time", fallback="").strip(),
                        "service": parser.get(section, "service", fallback="unknown").strip(),
                    },
                )
            )

        for idx, data in sorted(rows):
            self._last_idx_by_file[key] = idx
            if not emit_existing:
                continue

            message = data["message"]
            service = data["service"]
            service_low = service.lower()
            low = message.lower()
            is_donate = "донат" in low or any(
                marker in service_low
                for marker in ("donationalerts", "donatepay", "donate")
            )

            if is_donate:
                platform = "donation"
                kind = "donation"
            elif service_low in {"twitch", "twitch_chat"}:
                platform = "twitch"
                kind = "chat"
            elif service_low in {"youtube", "youtube_chat"}:
                platform = "youtube"
                kind = "chat"
            elif service_low in {"vk", "vkvideolive", "vkplay", "vk_video_live"}:
                platform = "vk"
                kind = "chat"
            elif service_low in {"stream_elements", "streamelements", "vkvideolive_system"}:
                platform = service_low
                kind = "system"
            else:
                platform = service_low or "axelchat"
                kind = "chat"

            is_stream_start = any(
                token in low
                for token in (
                    "is now live",
                    "стрим запущен",
                    "начал стрим",
                    "началась трансляция",
                )
            )
            is_stream_end = any(
                token in low
                for token in (
                    "stream ended",
                    "стрим завершен",
                    "стрим закончился",
                    "трансляция завершена",
                )
            )
            if is_stream_start or is_stream_end:
                kind = "system"

            mention = any(x in low for x in ("векса", "vexa", "мия", "мию"))
            priority = (
                0
                if is_donate
                else 1
                if mention or platform == "discord_voice"
                else 3
                if kind == "chat"
                else 3
            )

            event_timestamp = self._event_timestamp(data["time"])
            payload = {
                "priority": priority,
                "timestamp": event_timestamp,
                "author": data["author"] or "Anon",
                "user_id": data["author_id"],
                "message": message,
                "service": service or "axelchat",
                "platform": platform,
                "kind": kind,
                "is_donate": is_donate,
                "message_id": str(idx),
                "session_id": session_id,
                "source_time": data["time"],
            }
            self.loop.call_soon_threadsafe(self.queue_submit, payload)

    @staticmethod
    def _session_id(path: Path) -> str:
        for part in reversed(path.resolve().parts):
            if _SESSION_RE.fullmatch(part):
                return part
        return ""

    @staticmethod
    def _event_timestamp(raw: str) -> float:
        if not raw:
            return time.time()
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return time.time()
