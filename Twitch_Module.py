from __future__ import annotations

import asyncio
import re
import ssl
import time
from collections.abc import Awaitable, Callable

import config
from logger import log_event


IRC_HOST = "irc.chat.twitch.tv"
IRC_PORT = 6697

_PRIVMSG_RE = re.compile(
    r"^(?:@(?P<tags>\S+)\s+)?:(?P<prefix>\S+)\s+"
    r"PRIVMSG\s+(?P<target>#[^\s]+)\s+:(?P<message>.*)$"
)


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

        channel = config.TWITCH_CHANNEL.strip().lower().lstrip("#")
        token = config.TWITCH_TOKEN.strip()
        if not channel or not token:
            log_event(
                "TWITCH_ERR",
                "Для Twitch IRC нужны TWITCH_CHANNEL и TWITCH_TOKEN.",
            )
            return

        username = (
            config.TWITCH_BOT_USERNAME or config.TWITCH_CHANNEL or "vexa"
        ).strip().lower()
        token = token.removeprefix("oauth:")
        self._stop = False
        delay = 1.0

        while not self._stop:
            writer: asyncio.StreamWriter | None = None
            try:
                reader, writer = await asyncio.open_connection(
                    IRC_HOST,
                    IRC_PORT,
                    ssl=ssl.create_default_context(),
                )
                self._writer = writer
                writer.write(f"PASS oauth:{token}\r\n".encode("utf-8"))
                writer.write(f"NICK {username}\r\n".encode("utf-8"))
                writer.write(
                    b"CAP REQ :twitch.tv/tags twitch.tv/commands "
                    b"twitch.tv/membership\r\n"
                )
                writer.write(f"JOIN #{channel}\r\n".encode("utf-8"))
                await writer.drain()

                log_event("TWITCH", f"IRC подключён к #{channel}.")
                delay = 1.0

                while not self._stop:
                    raw = await reader.readline()
                    if not raw:
                        raise ConnectionError("Twitch IRC соединение закрыто")

                    line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                    if line.startswith("PING"):
                        writer.write(b"PONG :tmi.twitch.tv\r\n")
                        await writer.drain()
                        continue

                    event = self._parse_privmsg(line)
                    if event is None or self.event_callback is None:
                        continue

                    result = self.event_callback(event)
                    if asyncio.iscoroutine(result):
                        await result

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not self._stop:
                    log_event(
                        "TWITCH_ERR",
                        f"IRC ошибка: {exc}; повтор через {delay:.0f}с",
                    )
                    await asyncio.sleep(delay)
                    delay = min(delay * 2.0, 60.0)
            finally:
                if writer is not None:
                    writer.close()
                    try:
                        await writer.wait_closed()
                    except (OSError, RuntimeError):
                        pass
                if self._writer is writer:
                    self._writer = None

    @staticmethod
    def _parse_tags(raw_tags: str) -> dict[str, str]:
        """Parse IRCv3 tags and decode the escapes used by Twitch."""
        result: dict[str, str] = {}
        for item in raw_tags.split(";"):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            value = (
                value.replace(r"\s", " ")
                .replace(r"\:", ";")
                .replace(r"\r", "\r")
                .replace(r"\n", "\n")
                .replace(r"\\", "\\")
            )
            result[key] = value
        return result

    @classmethod
    def _parse_privmsg(cls, line: str) -> dict | None:
        match = _PRIVMSG_RE.match(line)
        if match is None:
            return None

        tags = cls._parse_tags(match.group("tags") or "")
        prefix = match.group("prefix")
        raw_author = prefix.split("!", 1)[0]
        if raw_author.startswith(":"):
            raw_author = raw_author[1:]

        author = tags.get("display-name") or raw_author or "unknown"
        return {
            "timestamp": time.time(),
            "author": author,
            "real_name": raw_author,
            "user_id": tags.get("user-id", ""),
            "message": match.group("message"),
            "service": "twitch",
            "platform": "twitch",
            "channel": match.group("target").lstrip("#"),
            "kind": "chat",
        }

    async def send_message(self, message: str) -> bool:
        writer = self._writer
        channel = config.TWITCH_CHANNEL.strip().lower().lstrip("#")
        text = " ".join(str(message).splitlines()).strip()
        if writer is None or not channel or not text:
            return False

        # Prevent user/model text from injecting additional IRC commands.
        text = text.replace("\r", " ").replace("\n", " ")[:500]
        writer.write(f"PRIVMSG #{channel} :{text}\r\n".encode("utf-8"))
        await writer.drain()
        return True

    def stop(self) -> None:
        self._stop = True
        writer = self._writer
        if writer is not None:
            writer.close()


twitch_client = TwitchChatClient()
