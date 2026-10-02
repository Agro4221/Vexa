from __future__ import annotations

import asyncio
import ctypes
import inspect
import time
from pathlib import Path
from typing import Optional

import config
from Vexa_State import state
from logger import log_event


class VexaVision:
    def __init__(self) -> None:
        self.model = None
        self.tokenizer = None
        self.device = "cpu"
        self.last_description = "Пока ничего не вижу."
        self.last_path: Optional[str] = None
        self.last_analyzed_at: Optional[float] = None
        self._load_error: Optional[Exception] = None
        self._lock = asyncio.Lock()

    def _apply_compat_patch(self) -> None:
        if not config.VISION_ENABLE_TRANSFORMERS_COMPAT_PATCH:
            return
        try:
            from transformers.modeling_attn_mask_utils import AttentionMaskConverter

            original = AttentionMaskConverter._ignore_causal_mask_sdpa
            if "is_training" in inspect.signature(original).parameters:
                return

            @staticmethod
            def patched(*args, **kwargs):
                kwargs.pop("is_training", None)
                return original(*args, **kwargs)

            AttentionMaskConverter._ignore_causal_mask_sdpa = patched
            log_event(
                "EYES",
                "Включён точечный transformers compatibility patch.",
            )
        except Exception as exc:
            log_event(
                "EYES",
                f"Compat patch пропущен: {exc}",
            )

    def _load_model_sync(self) -> None:
        if (
            self.model is not None
            or self._load_error is not None
            or not config.USE_VISION
        ):
            return

        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            self._apply_compat_patch()
            if config.VISION_DEVICE == "auto":
                self.device = (
                    "cuda" if torch.cuda.is_available() else "cpu"
                )
            else:
                self.device = config.VISION_DEVICE

            self.model = AutoModelForCausalLM.from_pretrained(
                config.VISION_MODEL_ID,
                trust_remote_code=True,
                revision=config.VISION_MODEL_REVISION,
            ).to(self.device)
            self.tokenizer = AutoTokenizer.from_pretrained(
                config.VISION_MODEL_ID,
                revision=config.VISION_MODEL_REVISION,
            )
            log_event(
                "EYES",
                f"Vision model loaded on {self.device}.",
            )
        except Exception as exc:
            self._load_error = exc
            log_event(
                "EYES_ERR",
                f"Ошибка загрузки зрения: {exc}",
            )

    @staticmethod
    def _parse_region() -> tuple[int, int, int, int] | None:
        value = config.VISION_REGION.strip()
        if not value:
            return None
        try:
            parts = [int(item.strip()) for item in value.split(",")]
            if len(parts) != 4:
                raise ValueError
            x, y, width, height = parts
            if width <= 0 or height <= 0:
                raise ValueError
            return x, y, width, height
        except ValueError:
            log_event(
                "EYES_ERR",
                "VISION_REGION должен иметь формат x,y,width,height.",
            )
            return None

    @staticmethod
    def _find_window_bbox(title: str) -> tuple[int, int, int, int] | None:
        if not title:
            return None
        if hasattr(ctypes, "windll"):
            from ctypes import wintypes
            user32 = ctypes.windll.user32
            matches: list[tuple[int, int, int, int]] = []

            EnumWindowsProc = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
            )

            def callback(hwnd, _lparam):
                buffer = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(
                    hwnd,
                    buffer,
                    512,
                )
                if title.lower() in buffer.value.lower():
                    rect = wintypes.RECT()
                    if user32.GetWindowRect(
                        hwnd,
                        ctypes.byref(rect),
                    ):
                        matches.append(
                            (
                                rect.left,
                                rect.top,
                                rect.right - rect.left,
                                rect.bottom - rect.top,
                            )
                        )
                        return False
                return True

            user32.EnumWindows(EnumWindowsProc(callback), 0)
            if matches:
                return matches[0]
        return None

    def take_screenshot(self) -> Optional[str]:
        try:
            from PIL import ImageGrab

            source = config.VISION_SOURCE
            if source == "region":
                bbox = self._parse_region()
                if bbox is None:
                    return None
                x, y, width, height = bbox
                image = ImageGrab.grab(
                    bbox=(x, y, x + width, y + height),
                    all_screens=True,
                )
            elif source == "window":
                bbox = self._find_window_bbox(
                    config.VISION_WINDOW_TITLE
                )
                if bbox is None:
                    log_event(
                        "EYES_ERR",
                        f"Окно зрения не найдено: {config.VISION_WINDOW_TITLE}",
                    )
                    return None
                x, y, width, height = bbox
                image = ImageGrab.grab(
                    bbox=(x, y, x + width, y + height),
                    all_screens=True,
                )
            else:
                try:
                    image = ImageGrab.grab(all_screens=True)
                except TypeError:
                    import pyautogui
                    image = pyautogui.screenshot()

            image = image.convert("RGB")
            if image.width > config.VISION_MAX_IMAGE_WIDTH:
                ratio = (
                    config.VISION_MAX_IMAGE_WIDTH
                    / image.width
                )
                image = image.resize(
                    (
                        config.VISION_MAX_IMAGE_WIDTH,
                        int(image.height * ratio),
                    )
                )

            config.VISION_DIR.mkdir(
                parents=True,
                exist_ok=True,
            )
            if config.VISION_SAVE_LAST_ONLY:
                path = config.VISION_DIR / "last_view.png"
            else:
                path = config.VISION_DIR / (
                    f"view_{int(time.time() * 1000)}.png"
                )
            image.save(path)
            self.last_path = str(path)
            state.set_vision(
                self.last_description,
                str(path),
            )
            return str(path)
        except Exception as exc:
            log_event(
                "EYES_ERR",
                f"Скриншот не получен: {exc}",
            )
            return None

    def analyze_screen_sync(
        self,
        question: str | None = None,
    ) -> str:
        self._load_model_sync()
        if self.model is None:
            return self.last_description

        path = self.take_screenshot()
        if not path:
            return self.last_description

        try:
            from PIL import Image
            import torch

            with Image.open(path) as image:
                image = image.convert("RGB")
                embeddings = self.model.encode_image(image)
            with torch.no_grad():
                answer = self.model.answer_question(
                    embeddings,
                    question or config.VISION_PROMPT,
                    self.tokenizer,
                )

            description = str(answer).strip()
            if description:
                self.last_description = description
                self.last_analyzed_at = time.time()
                state.set_vision(
                    description,
                    path,
                )
        except Exception as exc:
            log_event(
                "EYES_ERR",
                f"Ошибка анализа: {exc}",
            )
        return self.last_description

    async def analyze_screen(
        self,
        question: str | None = None,
    ) -> str:
        async with self._lock:
            return await asyncio.to_thread(
                self.analyze_screen_sync,
                question,
            )

    async def autonomous_loop(self) -> None:
        if not config.USE_VISION:
            return
        while True:
            await self.analyze_screen(
                config.VISION_PROMPT
            )
            await asyncio.sleep(
                config.VISION_INTERVAL
            )


vexa_eyes = VexaVision()