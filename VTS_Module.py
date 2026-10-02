from __future__ import annotations

import asyncio
import random

import config
from logger import log_event


class VexaVTS:
    def __init__(self) -> None:
        self.vts = None
        self.is_connected = False
        self._connect_lock = asyncio.Lock()

    async def connect(self) -> bool:
        if not config.VTS_ENABLED:
            return False
        async with self._connect_lock:
            try:
                if self.vts is None:
                    import pyvts

                    self.vts = pyvts.vts(
                        plugin_info={
                            "plugin_name": config.VTS_PLUGIN_NAME,
                            "developer": config.VTS_PLUGIN_DEVELOPER,
                            "authentication_token_path": str(config.VTS_TOKEN_PATH),
                        }
                    )
                if self.is_connected:
                    return True
                await self.vts.connect()
                await self.vts.request_authenticate_token()
                self.is_connected = bool(await self.vts.request_authenticate())
                log_event("VTS", "VTube Studio подключён и авторизован." if self.is_connected else "VTS авторизация не подтверждена.")
                return self.is_connected
            except Exception as exc:
                self.is_connected = False
                log_event("VTS_ERR", f"Ошибка подключения: {exc}")
                return False

    async def close(self) -> None:
        self.is_connected = False
        if self.vts is not None:
            try:
                await self.vts.close()
            except Exception:
                pass

    async def trigger_emotion(self, emotion_name: str) -> bool:
        hotkeys = {
            "joy": config.VTS_HOTKEY_JOY,
            "angry": config.VTS_HOTKEY_ANGRY,
            "surprise": config.VTS_HOTKEY_SURPRISE,
        }
        hotkey = hotkeys.get(emotion_name.lower(), emotion_name)
        if not self.is_connected or self.vts is None:
            return False
        try:
            await self.vts.request(self.vts.vts_request.requestTriggerHotKey(hotkeyID=hotkey))
            return True
        except Exception as exc:
            self.is_connected = False
            log_event("VTS_ERR", f"Hotkey {hotkey}: {exc}")
            return False

    async def set_parameter(self, parameter: str, value: float) -> bool:
        if not self.is_connected or self.vts is None:
            return False
        try:
            await self.vts.request(
                self.vts.vts_request.requestSetParameterValue(parameter=parameter, value=float(value))
            )
            return True
        except Exception as exc:
            self.is_connected = False
            log_event("VTS_ERR", f"Parameter {parameter}: {exc}")
            return False

    async def start_idle_motion(self) -> None:
        if not config.VTS_ENABLED or not config.VTS_IDLE_MOTION:
            return
        while True:
            try:
                if not self.is_connected:
                    await self.connect()
                    await asyncio.sleep(3)
                    continue
                await self.set_parameter("ParamAngleX", random.uniform(-5, 5))
                await self.set_parameter("ParamAngleY", random.uniform(-3, 3))
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event("VTS_ERR", f"Idle motion: {exc}")
                await asyncio.sleep(5)


vexa_vts = VexaVTS()
