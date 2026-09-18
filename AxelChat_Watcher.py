from __future__

import configparser
import time
from pathlib import Path
from typing import Any, Callable

from logger import log_event


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
                        "message": parser.get(section, "message", fallback="").strip(),
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
            low = message.lower()
            service_low = service.lower()
            is_donate = "донат" in low or any(
                x in service_low for x in ("donationalerts", "donatepay", "donate")
            )
            priority = 0 if is_donate else 1 if any(
                x in low for x in ("векса", "vexa", "мия", "мию")
            ) else 3
            payload = {
                "priority": priority,
                "timestamp": time.time(),
                "author": data["author"] or "Anon",
                "message": message,
                "service": service or "axelchat",
                "is_donate": is_donate,
                "message_id": str(idx),
            }
            self.loop.call_soon_threadsafe(self.queue_submit, payload)
