from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import config
from logger import log_event


SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


class YouTubeLiveClient:
    """Isolated YouTube Live Chat/OAuth adapter."""

    def __init__(
        self,
        event_callback: Callable[[dict], Awaitable[None] | None] | None = None,
    ) -> None:
        self.event_callback = event_callback
        self._stop = False
        self._service = None
        self._page_token: str | None = None
        self.live_chat_id: str | None = (
            config.YT_LIVE_CHAT_ID or None
        )
        self._seen_message_ids: set[str] = set()
        self._warmed_up = False

    def _load_service(self):
        if self._service is not None:
            return self._service

        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        token_path = Path(config.YT_TOKEN_FILE)
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path),
                SCOPES,
            )

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        if not creds or not creds.valid:
            client_secret_file = Path(config.YT_CLIENT_SECRET_FILE)
            if client_secret_file.exists():
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secret_file),
                    SCOPES,
                )
            elif config.YT_CLIENT_ID and config.YT_CLIENT_SECRET:
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": config.YT_CLIENT_ID,
                            "client_secret": config.YT_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": ["http://localhost"],
                        }
                    },
                    SCOPES,
                )
            else:
                raise RuntimeError(
                    "YouTube OAuth credentials не заданы"
                )
            creds = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent",
            )

        token_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        token_path.write_text(
            creds.to_json(),
            encoding="utf-8",
        )
        self._service = build(
            "youtube",
            "v3",
            credentials=creds,
            cache_discovery=False,
        )
        return self._service

    def _get_live_chat_id_sync(self) -> str | None:
        if config.YT_LIVE_CHAT_ID:
            return config.YT_LIVE_CHAT_ID

        service = self._load_service()
        response = (
            service.liveBroadcasts()
            .list(
                part="id,snippet,status",
                broadcastStatus="active",
                broadcastType="all",
                mine=True,
                maxResults=10,
            )
            .execute()
        )

        for item in response.get("items", []):
            live_chat_id = item.get(
                "snippet",
                {},
            ).get("liveChatId")
            if live_chat_id:
                return str(live_chat_id)
        return None

    async def run(self) -> None:
        if not config.YT_ENABLED:
            log_event("YOUTUBE", "YouTube direct chat отключён.")
            return

        self._stop = False
        delay = 10.0
        while not self._stop:
            try:
                live_chat_id = await asyncio.to_thread(
                    self._get_live_chat_id_sync
                )
                if not live_chat_id:
                    await asyncio.sleep(15)
                    continue

                if live_chat_id != self.live_chat_id:
                    self._page_token = None
                    self._seen_message_ids.clear()
                    self._warmed_up = False

                self.live_chat_id = live_chat_id
                await self._poll_loop(live_chat_id)
                delay = 10.0
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event(
                    "YOUTUBE_ERR",
                    f"YouTube ошибка: {exc}; повтор через {delay:.0f}с",
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 60.0)

    async def _poll_loop(self, live_chat_id: str) -> None:
        while not self._stop:
            result = await asyncio.to_thread(
                self._list_messages_sync,
                live_chat_id,
            )
            polling_ms = int(
                result.get(
                    "pollingIntervalMillis",
                    config.YT_POLLING_DEFAULT_SECONDS * 1000,
                )
            )

            items = result.get("items", [])
            for item in items:
                message_id = str(item.get("id", ""))
                if message_id and message_id in self._seen_message_ids:
                    continue
                if message_id:
                    self._seen_message_ids.add(message_id)

                snippet = item.get("snippet", {})
                author_details = item.get(
                    "authorDetails",
                    {},
                )
                message = snippet.get(
                    "displayMessage",
                    "",
                )
                if not message:
                    continue
                if not self._warmed_up:
                    continue

                event = {
                    "priority": None,
                    "timestamp": __import__("time").time(),
                    "author": author_details.get(
                        "displayName",
                        "YouTube user",
                    ),
                    "real_name": author_details.get(
                        "displayName",
                        "",
                    ),
                    "message": message,
                    "service": "youtube",
                    "platform": "youtube",
                    "user_id": author_details.get(
                        "channelId",
                        "",
                    ),
                    "message_id": message_id,
                    "kind": "chat",
                }
                if self.event_callback:
                    callback_result = self.event_callback(event)
                    if asyncio.iscoroutine(callback_result):
                        await callback_result

            self._warmed_up = True
            await asyncio.sleep(
                max(1.0, polling_ms / 1000.0)
            )

    def _list_messages_sync(self, live_chat_id: str) -> dict:
        service = self._load_service()
        kwargs = {
            "part": "id,snippet,authorDetails",
            "liveChatId": live_chat_id,
            "maxResults": 200,
        }
        if self._page_token:
            kwargs["pageToken"] = self._page_token
        response = (
            service.liveChatMessages()
            .list(**kwargs)
            .execute()
        )
        self._page_token = response.get("nextPageToken")
        return response

    def update_broadcast_title_sync(
        self,
        video_id: str,
        title: str,
    ) -> bool:
        service = self._load_service()
        current = (
            service.liveBroadcasts()
            .list(
                part="id,snippet",
                id=video_id,
            )
            .execute()
        )
        items = current.get("items", [])
        if not items:
            raise RuntimeError(
                f"YouTube broadcast не найден: {video_id}"
            )
        snippet = dict(
            items[0].get(
                "snippet",
                {},
            )
        )
        snippet["title"] = title[:128]
        service.liveBroadcasts().update(
            part="snippet",
            body={
                "id": video_id,
                "snippet": snippet,
            },
        ).execute()
        return True

    def moderate_user_sync(
        self,
        user_channel_id: str,
        action: str = "ban",
        duration_seconds: int | None = None,
        reason: str = "",
        message_id: str = "",
    ) -> bool:
        if not user_channel_id:
            raise ValueError(
                "YouTube moderation requires user channel ID"
            )
        service = self._load_service()
        live_chat_id = (
            self.live_chat_id
            or self._get_live_chat_id_sync()
        )
        if not live_chat_id:
            raise RuntimeError(
                "YouTube live chat ID не найден"
            )

        if action == "delete_message":
            if not message_id:
                raise ValueError(
                    "delete_message requires message_id"
                )
            (
                service.liveChatMessages()
                .delete(id=message_id)
                .execute()
            )
            log_event(
                "MODERATION",
                f"YouTube delete_message: {message_id}",
            )
            return True

        if action == "timeout":
            snippet = {
                "liveChatId": live_chat_id,
                "type": "temporary",
                "bannedUserDetails": {
                    "channelId": str(user_channel_id),
                },
                "banDurationSeconds": max(
                    1,
                    min(
                        1_209_600,
                        int(duration_seconds or 300),
                    ),
                ),
                "displayName": "",
            }
        elif action == "ban":
            snippet = {
                "liveChatId": live_chat_id,
                "type": "permanent",
                "bannedUserDetails": {
                    "channelId": str(user_channel_id),
                },
            }
        else:
            raise ValueError(
                f"Unsupported YouTube moderation action: {action}"
            )

        (
            service.liveChatBans()
            .insert(
                part="snippet",
                body={"snippet": snippet},
            )
            .execute()
        )
        log_event(
            "MODERATION",
            f"YouTube {action}: user={user_channel_id}",
        )
        return True

    async def send_message(self, message: str) -> bool:
        if not message.strip():
            return False
        try:
            if not self._service:
                await asyncio.to_thread(
                    self._load_service
                )
            live_chat_id = (
                self.live_chat_id
                or await asyncio.to_thread(
                    self._get_live_chat_id_sync
                )
            )
            if not live_chat_id:
                return False
            await asyncio.to_thread(
                self._send_message_sync,
                live_chat_id,
                message[:200],
            )
            return True
        except Exception as exc:
            log_event(
                "YOUTUBE_ERR",
                f"Отправка сообщения не удалась: {exc}",
            )
            return False

    def _send_message_sync(
        self,
        live_chat_id: str,
        message: str,
    ) -> None:
        service = self._load_service()
        (
            service.liveChatMessages()
            .insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {
                            "messageText": message,
                        },
                    }
                },
            )
            .execute()
        )

    def stop(self) -> None:
        self._stop = True


youtube_client = YouTubeLiveClient()
