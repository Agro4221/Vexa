from __future__ import annotations

import asyncio
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import config
from logger import log_event

_model = None
_model_error: Optional[Exception] = None
_model_lock = threading.Lock()
_transcribe_lock = threading.Lock()

HOT_WORDS = "Cyberpunk, Edgerunners, Jostik, Жостик, Vexa, Векса, Resident Evil, Мия, Мию, Омск, Резик"
HALLUCINATIONS = (
    "музыка",
    "динамичная музыка",
    "спокойная музыка",
    "тихая музыка",
    "продолжение следует",
    "субтитры",
    "спасибо за просмотр",
    "редактор",
    "сообщество",
    "озвучено",
    "подготовлено",
    "перевод",
)


def _get_model():
    global _model, _model_error
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        if _model_error is not None:
            raise RuntimeError("Whisper недоступен") from _model_error
        try:
            from faster_whisper import WhisperModel

            log_event(
                "EARS",
                f"Загрузка Whisper {config.STT_MODEL_SIZE} на {config.STT_DEVICE}/{config.STT_COMPUTE_TYPE}",
            )
            _model = WhisperModel(
                config.STT_MODEL_SIZE,
                device=config.STT_DEVICE,
                compute_type=config.STT_COMPUTE_TYPE,
            )
            return _model
        except Exception as exc:
            _model_error = exc
            log_event("EARS_ERR", f"Не удалось загрузить Whisper: {exc}")
            raise


def transcribe_file(audio_path: str | os.PathLike[str]) -> str:
    model = _get_model()
    with _transcribe_lock:
        segments, _ = model.transcribe(
            str(audio_path),
            language=config.STT_LANGUAGE,
            beam_size=config.STT_BEAM_SIZE,
            initial_prompt=HOT_WORDS,
            vad_filter=True,
        )
        parts = []
        for segment in segments:
            if getattr(segment, "no_speech_prob", 0.0) > config.STT_HALLUCINATION_THRESHOLD:
                continue
            text = segment.text.strip()
            if len(text) < 2 or any(junk in text.lower() for junk in HALLUCINATIONS):
                continue
            parts.append(text)
        return " ".join(parts).strip()


async def transcribe_bytes(data: bytes, suffix: str = ".wav") -> str:
    fd, name = tempfile.mkstemp(prefix="vexa_stt_", suffix=suffix, dir=config.AUDIO_DIR)
    os.close(fd)
    path = Path(name)
    try:
        path.write_bytes(data)
        return await asyncio.to_thread(transcribe_file, path)
    finally:
        path.unlink(missing_ok=True)


def listen_sync() -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = False
    recognizer.energy_threshold = config.STT_ENERGY_THRESHOLD
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1.5)
        log_event("EARS", "Локальный микрофон активирован.")
        while True:
            try:
                audio = recognizer.listen(source, phrase_time_limit=config.STT_MAX_SECONDS)
                with tempfile.NamedTemporaryFile(
                    prefix="vexa_mic_", suffix=".wav", dir=config.AUDIO_DIR, delete=False
                ) as handle:
                    handle.write(audio.get_wav_data())
                    path = handle.name
                try:
                    text = transcribe_file(path)
                finally:
                    Path(path).unlink(missing_ok=True)
                if text and len(text) >= 3:
                    log_event("EARS", f"Распознано: {text}")
                    return text
            except Exception as exc:
                log_event("EARS_ERR", f"Ошибка локального STT: {exc}")
                time.sleep(1)


async def listen() -> str:
    return await asyncio.to_thread(listen_sync)
