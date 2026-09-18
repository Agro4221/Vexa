from __future__

import asyncio
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

import config
from logger import log_event
from text_utils import prepare_text_for_tts

_model = None
_model_error: Optional[Exception] = None
_model_lock = threading.Lock()
_tts_lock = threading.Lock()


def _ensure_model():
    global _model, _model_error
    if _model is not None:
        return
    with _model_lock:
        if _model is not None:
            return
        if _model_error is not None:
            raise RuntimeError("Silero TTS недоступен") from _model_error
        path = config.VOICE_MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            if not config.VOICE_AUTO_DOWNLOAD:
                raise FileNotFoundError(f"TTS-модель отсутствует: {path}")
            import torch.hub

            log_event("VOICE", "Скачиваю Silero V5 модель.")
            torch.hub.download_url_to_file(config.VOICE_MODEL_URL, str(path), progress=True)
        try:
            import torch

            model = torch.package.PackageImporter(str(path)).load_pickle("tts_models", "model")
            model.to(torch.device("cpu"))
            _model = model
            log_event("VOICE", f"Silero TTS загружен: speaker={config.SPEAKER}")
        except Exception as exc:
            _model_error = exc
            log_event("VOICE_ERR", f"Ошибка загрузки Silero: {exc}")
            raise


def generate_audio(text: str, file_path: str | Path | None = None) -> str:
    _ensure_model()
    clean = prepare_text_for_tts(text)
    if not clean:
        raise ValueError("Пустой текст для TTS")
    output = (
        Path(file_path)
        if file_path is not None
        else config.AUDIO_DIR / f"tts_{int(time.time()*1000)}_{uuid.uuid4().hex[:8]}.wav"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _tts_lock:
            try:
                _model.save_wav(
                    text=clean,
                    speaker=config.SPEAKER,
                    sample_rate=config.SAMPLE_RATE,
                    audio_path=str(output),
                    put_accent=True,
                    put_yo=True,
                )
            except TypeError:
                _model.save_wav(
                    text=clean,
                    speaker=config.SPEAKER,
                    sample_rate=config.SAMPLE_RATE,
                    audio_path=str(output),
                )
        return str(output)
    except Exception:
        cleanup_audio(output)
        raise


async def generate_audio_async(text: str) -> str:
    return await asyncio.to_thread(generate_audio, text)


def cleanup_audio(path: str | Path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as exc:
        log_event("VOICE_ERR", f"Не удалось удалить audio-файл {path}: {exc}")


def speak(text: str) -> None:
    path = generate_audio(text)
    try:
        import simpleaudio as sa

        sa.WaveObject.from_wave_file(path).play().wait_done()
    finally:
        cleanup_audio(path)


def ffmpeg_available() -> bool:
    try:
        return subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        ).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
