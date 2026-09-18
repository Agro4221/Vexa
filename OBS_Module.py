from __future__ import annotations

import asyncio

import config
from logger import log_event


class OBSController:
    """Optional OBS WebSocket v5 control layer, kept out of the core runtime path."""

    def __init__(self) -> None:
        self._client = None
        self._lock = asyncio.Lock()

    def _get_client(self):
        if self._client is not None:
            return self._client
        import obsws_python as obs

        self._client = obs.ReqClient(
            host=config.OBS_HOST,
            port=config.OBS_PORT,
            password=config.OBS_PASSWORD,
            timeout=5,
        )
        return self._client

    async def connect(self) -> bool:
        if not config.OBS_ENABLED:
            return False
        async with self._lock:
            try:
                client = await asyncio.to_thread(self._get_client)
                await asyncio.to_thread(client.get_version)
                log_event("OBS", "OBS WebSocket подключён.")
                return True
            except Exception as exc:
                self._client = None
                log_event("OBS_ERR", f"OBS недоступен: {exc}")
                return False

    async def set_scene(self, scene: str) -> bool:
        if not scene or not await self.connect():
            return False
        try:
            await asyncio.to_thread(self._get_client().set_current_program_scene, scene)
            return True
        except Exception as exc:
            log_event("OBS_ERR", f"Смена сцены не удалась: {exc}")
            return False

    async def start_stream(self) -> bool:
        if not await self.connect():
            return False
        try:
            await asyncio.to_thread(self._get_client().start_stream)
            return True
        except Exception as exc:
            log_event("OBS_ERR", f"Запуск стрима не удался: {exc}")
            return False

    async def stop_stream(self) -> bool:
        if not await self.connect():
            return False
        try:
            await asyncio.to_thread(self._get_client().stop_stream)
            return True
        except Exception as exc:
            log_event("OBS_ERR", f"Остановка стрима не удалась: {exc}")
            return False

    async def set_input_mute(self, input_name: str, muted: bool) -> bool:
        if not input_name or not await self.connect():
            return False
        try:
            await asyncio.to_thread(self._get_client().set_input_mute, input_name, bool(muted))
            return True
        except Exception as exc:
            log_event("OBS_ERR", f"Mute {input_name} не удался: {exc}")
            return False


obs_controller = OBSController()
