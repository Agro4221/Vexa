from __future__ import annotations

import asyncio
import re
import ssl
from collections.abc import Awaitable, Callable

import config
from logger import log_event


IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697


class TwitchChatClient:
    """Small isolated Twitch IRC client for optional direct chat I/O."""

    def __init__(
        self,
        event_callback: Callable[[dict], Awaitable[None] | None] | None = None,
    ) -> None:
        self.event_callback = event_callback
        self._writer: asyncio.StreamWriter | None = None
        self._stop = False

    async def connect(self) -> None:
        if not config.TWITCH_ENABLED:
            log_event("TWITCH", "Twitch direct chat отключён.")
            return

        self._stop = False
        delay = 1.0
        while not self._stop:
            try:
                context = ssl.create_default_context()
                reader, writer = await asyncio.open_connection(
                    IRC_HOST,
                    IRC_PORT,
                    ssl=context,
                )
                self._writer = writer
                username = (
                    config.TWITCH_BOT_USERNAME
                    or config.TWITCH_CHANNEL
                    or "vexa"
                ).lower()
                channel = config.TWITCH_CHANNEL.lower().lstrip("#")

                writer.write(f"PASS oauth:{config.TWITCH_TOKEN}
".encode())
                writer.write(f"NICK {username}
".encode())
                writer.write(
                    b"CAP REQ :twitch.tv/tags twitch.tv/commands twitch.tv/membership
"
                )
                writer.write(f"JOIN #{channel}
".encode())
                await writer.drain()

                log_event("TWITCH", f"IRC подключён к #{channel}.")
                delay = 1.0

                while not self._stop:
                    raw = await reader.readline()
                    if not raw:
                        raise ConnectionError(
                            "Twitch IRC соединение закрыто"
                        )
                    line = raw.decode(
                        "utf-8",
                        errors="replace",
                    ).rstrip("
")

                    if line.startswith("PING"):
                        writer.write(
                            b"PONG :tmi.twitch.tv
"
                        )
                        await writer.drain()
                        continue

                    event = self._parse_privmsg(line)
                    if event and self.event_callback:
                        result = self.event_callback(event)
                        if asyncio.iscoroutine(result):
                            await result

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event(
                    "TWITCH_ERR",
                    f"IRC ошибка: {exc}; повтор через {delay:.0f}с",
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 60.0)
            finally:
                if self._writer is not None:
                    self._writer.close()
                    try:
                        await self._writer.wait_closed()
                    except Exception:
                        pass
                    self._writer = None

    @staticmethod
    def _parse_tags(raw_tags: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for item in raw_tags.split(";"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            value = (
                value.replace(r"\s", " ")
                .replace(r"\:", ":")
                .replace(r"\;", ";")
                .replace(r"\", "\")
            )
            result[key] = value
        return result

    @classmethod
    def _parse_privmsg(cls, line: str) -> dict | None:
        if " PRIVMSG #" not in line or " :" not in line:
            return None

        prefix, message = line.rsplit(" :", 1)
        tags: dict[str, str] = {}
        if prefix.startswith("@"):
            raw_tags, prefix = prefix.split(" ", 1)
            tags = cls._parse_tags(raw_tags[1:])

        target_match = re.search(
            r"PRIVMSG #(S+)",
            prefix,
        )
        if not target_match:
            return None

        raw_author = ""
        if prefix.startswith(":"):
            raw_author = prefix[1:].split("!", 1)[0]

        author = tags.get("display-name") or raw_author or "unknown"
        return {
            "priority": None,
            "timestamp": __import__("time").time(),
            "author": author,
            "real_name": raw_author,
            "user_id": tags.get("user-id", ""),
            "message": message,
            "service": "twitch",
            "platform": "twitch",
            "channel": target_match.group(1),
            "kind": "chat",
        }

    async def send_message(self, message: str) -> bool:
        if not self._writer or not message.strip():
            return False
        channel = config.TWITCH_CHANNEL.lower().lstrip("#")
        if not channel:
            return False
        self._writer.write(
            f"PRIVMSG #{channel} :{message[:500]}
".encode("utf-8")
        )
        await self._writer.drain()
        return True

    def stop(self) -> None:
        self._stop = True


twitch_client = TwitchChatClient()
