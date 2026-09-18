from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

import config
from logger import log_event


SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


class YouTubeLiveClient:
    """YouTube Live chat client with persisted OAuth credentials and polling."""

    def __init__(self, event_callback: Callable[[dict], Awaitable[None] | None] | None = None) -> None:
        self.event_callback = event_callback
        self._stop = False
        self._service = None
        self._page_token: str | None = None
        self.live_chat_id: str | None = config.YT_LIVE_CHAT_ID or None
        self._seen_message_ids: set[str] = set()
        self._warmed_up = False

    def _load_service(self):
        if self._service is not None:
            return self._service
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow

        token_path = Path(config.YT_TOKEN_FILE)
        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        if not creds or not creds.valid:
            client_secret_file = Path(config.YT_CLIENT_SECRET_FILE)
            if client_secret_file.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_file), SCOPES)
            elif config.YT_CLIENT_ID and config.YT_CLIENT_SECRET:
                client_config = {
                    "installed": {
                        "client_id": config.YT_CLIENT_ID,
                        "client_secret": config.YT_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": ["http://localhost"],
                    }
                }
                flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            else:
                raise RuntimeError("YouTube OAuth credentials не заданы")
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")
        self._service = build("youtube", "v3", credentials=creds, cache_discovery=False)
        return self._service

    def _get_live_chat_id_sync(self) -> str | None:
        if config.YT_LIVE_CHAT_ID:
            return config.YT_LIVE_CHAT_ID
        service = self._load_service()
        kwargs = {
            "part": "id,snippet,status",
            "broadcastStatus": "active",
            "broadcastType": "all",
            "maxResults": 10,
        }
        kwargs["mine"] = True
        response = service.liveBroadcasts().list(**kwargs).execute()
        for item in response.get("items", []):
            live_chat_id = item.get("snippet", {}).get("liveChatId")
            if live_chat_id:
                return str(live_chat_id)
        return None

    async def run(self) -> None:
        if not config.YT_ENABLED:
            log_event("YOUTUBE", "YouTube чат отключён: OAuth не настроен.")
            return
        self._stop = False
        while not self._stop:
            try:
                live_chat_id = await asyncio.to_thread(self._get_live_chat_id_sync)
                if not live_chat_id:
                    await asyncio.sleep(15)
                    continue
                if live_chat_id != self.live_chat_id:
                    self._page_token = None
                    self._seen_message_ids.clear()
                    self._warmed_up = False
                self.live_chat_id = live_chat_id
                await self._poll_loop(live_chat_id)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("YOUTUBE_ERR", f"YouTube ошибка: {exc}; повтор через 10с")
                await asyncio.sleep(10)

    async def _poll_loop(self, live_chat_id: str) -> None:
        while not self._stop:
            result = await asyncio.to_thread(self._list_messages_sync, live_chat_id)
            polling_ms = int(result.get("pollingIntervalMillis", config.YT_POLLING_DEFAULT_SECONDS * 1000))
            items = result.get("items", [])
            for item in items:
                message_id = str(item.get("id", ""))
                if message_id and message_id in self._seen_message_ids:
                    continue
                if message_id:
                    self._seen_message_ids.add(message_id)
                snippet = item.get("snippet", {})
                author = item.get("authorDetails", {}).get("displayName", "YouTube user")
                message = snippet.get("displayMessage", "")
                if not message:
                    continue
                if not self._warmed_up:
                    continue
                event = {
                    "priority": None,
                    "author": author,
                    "message": message,
                    "service": "youtube",
                    "user_id": item.get("authorDetails", {}).get("channelId", ""),
                }
                if self.event_callback:
                    callback_result = self.event_callback(event)
                    if asyncio.iscoroutine(callback_result):
                        await callback_result
            self._warmed_up = True
            await asyncio.sleep(max(1.0, polling_ms / 1000.0))

    def _list_messages_sync(self, live_chat_id: str) -> dict:
        service = self._load_service()
        kwargs = {
            "part": "id,snippet,authorDetails",
            "liveChatId": live_chat_id,
            "maxResults": 200,
        }
        if self._page_token:
            kwargs["pageToken"] = self._page_token
        response = service.liveChatMessages().list(**kwargs).execute()
        self._page_token = response.get("nextPageToken")
        return response

    def update_broadcast_title_sync(self, video_id: str, title: str) -> bool:
        service = self._load_service()
        current = service.liveBroadcasts().list(part="id,snippet,contentDetails", id=video_id).execute()
        items = current.get("items", [])
        if not items:
            raise RuntimeError(f"YouTube broadcast не найден: {video_id}")
        snippet = dict(items[0].get("snippet", {}))
        snippet["title"] = title[:128]
        # The API replaces mutable properties in the selected part, so retain required snippet fields.
        body = {"id": video_id, "snippet": snippet}
        service.liveBroadcasts().update(part="snippet", body=body).execute()
        return True

    async def send_message(self, message: str) -> bool:
        if not message.strip():
            return False
        if not self._service:
            try:
                await asyncio.to_thread(self._load_service)
            except Exception as exc:
                log_event("YOUTUBE_ERR", f"OAuth недоступен для отправки: {exc}")
                return False
        live_chat_id = self.live_chat_id or await asyncio.to_thread(self._get_live_chat_id_sync)
        if not live_chat_id:
            return False
        try:
            await asyncio.to_thread(self._send_message_sync, live_chat_id, message[:200])
            return True
        except Exception as exc:
            log_event("YOUTUBE_ERR", f"Отправка сообщения не удалась: {exc}")
            return False

    def _send_message_sync(self, live_chat_id: str, message: str) -> None:
        service = self._load_service()
        service.liveChatMessages().insert(
            part="snippet",
            body={"snippet": {"liveChatId": live_chat_id, "type": "textMessageEvent", "textMessageDetails": {"messageText": message}}},
        ).execute()

    def stop(self) -> None:
        self._stop = True


youtube_client = YouTubeLiveClient()
