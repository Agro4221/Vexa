from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

APP_ROOT = Path(__file__).resolve().parent
ENV_FILE = APP_ROOT / ".env"
if load_dotenv is not None:
    load_dotenv(ENV_FILE)

def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default

def env_list(name: str, default: list[str] | None = None) -> list[str]:
    value = os.getenv(name)
    if not value:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]

DATA_DIR = Path(os.getenv("VEXA_DATA_DIR", APP_ROOT / "data"))
LOG_DIR = Path(os.getenv("VEXA_LOG_DIR", DATA_DIR / "logs"))
VISION_DIR = Path(os.getenv("VEXA_VISION_DIR", DATA_DIR / "vision"))
AUDIO_DIR = Path(os.getenv("VEXA_AUDIO_DIR", DATA_DIR / "audio"))
DB_PATH = Path(os.getenv("VEXA_DB_PATH", DATA_DIR / "streamer_brain.db"))
VTS_TOKEN_PATH = Path(os.getenv("VTS_TOKEN_PATH", APP_ROOT / "vts_token.txt"))

for _path in (DATA_DIR, LOG_DIR, VISION_DIR, AUDIO_DIR):
    _path.mkdir(parents=True, exist_ok=True)

CURRENT_MODEL = (
    os.getenv("VEXA_MODEL")
    or os.getenv("MIUU_MODEL")
    or "shayzinasimulation/red-angel-8b-rede-uncensored-abliterated"
)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_TIMEOUT = env_float("OLLAMA_TIMEOUT", 45.0)
MAX_HISTORY = env_int("MAX_HISTORY", 12)
MAX_CONTEXT_CHARS = env_int("MAX_CONTEXT_CHARS", 7000)
USE_WEB_SEARCH = env_bool("USE_WEB_SEARCH", True)
USE_STRUCTURED_OUTPUT = env_bool("USE_STRUCTURED_OUTPUT", True)

SEARCH_TRIGGERS = env_list(
    "SEARCH_TRIGGERS",
    ["найди", "погугли", "загугли", "кто такой", "что такое", "как найти", "интернет"],
)

VOICE_MODEL_PATH = Path(os.getenv("VOICE_MODEL_PATH", APP_ROOT / "v5_ru.pt"))
VOICE_MODEL_URL = os.getenv(
    "VOICE_MODEL_URL",
    "https://models.silero.ai/models/tts/ru/v5_ru.pt",
)
VOICE_AUTO_DOWNLOAD = env_bool("VOICE_AUTO_DOWNLOAD", True)
SPEAKER = os.getenv("VEXA_SPEAKER", os.getenv("SPEAKER", "baya"))
SAMPLE_RATE = env_int("VEXA_SAMPLE_RATE", env_int("SAMPLE_RATE", 48000))

STT_MODEL_SIZE = os.getenv("STT_MODEL_SIZE", "base")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")
STT_COMPUTE_TYPE = os.getenv(
    "STT_COMPUTE_TYPE", "float16" if STT_DEVICE == "cuda" else "int8"
)
STT_LANGUAGE = os.getenv("STT_LANGUAGE", "ru")
STT_BEAM_SIZE = env_int("STT_BEAM_SIZE", 5)
STT_MAX_SECONDS = env_int("STT_MAX_SECONDS", 10)
STT_ENERGY_THRESHOLD = env_int("STT_ENERGY_THRESHOLD", 450)
STT_HALLUCINATION_THRESHOLD = env_float("STT_NO_SPEECH_PROB", 0.6)

USE_VISION = env_bool("USE_VISION", True)
VISION_MODEL_ID = os.getenv("VISION_MODEL_ID", "vikhyatk/moondream2")
VISION_MODEL_REVISION = os.getenv("VISION_MODEL_REVISION", "2024-08-26")
VISION_DEVICE = os.getenv("VISION_DEVICE", "cpu")
VISION_MAX_IMAGE_WIDTH = env_int("VISION_MAX_IMAGE_WIDTH", 1920)
VISION_ENABLE_TRANSFORMERS_COMPAT_PATCH = env_bool(
    "VISION_ENABLE_TRANSFORMERS_COMPAT_PATCH", True
)

VTS_HOST = os.getenv("VTS_HOST", "localhost")
VTS_PORT = env_int("VTS_PORT", 8001)
VTS_PLUGIN_NAME = os.getenv("VTS_PLUGIN_NAME", "Vexa_AI")
VTS_PLUGIN_DEVELOPER = os.getenv("VTS_PLUGIN_DEVELOPER", "Agro4221")
VTS_HOTKEY_JOY = os.getenv("VTS_HOTKEY_JOY", "Joy")
VTS_HOTKEY_ANGRY = os.getenv("VTS_HOTKEY_ANGRY", "Angry")
VTS_HOTKEY_SURPRISE = os.getenv("VTS_HOTKEY_SURPRISE", "Surprise")
VTS_IDLE_MOTION = env_bool("VTS_IDLE_MOTION", True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_ENABLED = bool(DISCORD_TOKEN)
DISCORD_PREFIX = os.getenv("DISCORD_PREFIX", "!")
DISCORD_VOICE_REPLY = env_bool("DISCORD_VOICE_REPLY", True)
DISCORD_RECEIVE_VOICE = env_bool("DISCORD_RECEIVE_VOICE", True)
DISCORD_DEFAULT_GUILD_ID = env_int("DISCORD_DEFAULT_GUILD_ID", 0)
DISCORD_MIN_AUDIO_BYTES = env_int("DISCORD_MIN_AUDIO_BYTES", 24000)
DISCORD_MAX_AUDIO_BYTES = env_int("DISCORD_MAX_AUDIO_BYTES", 1920000)

TG_API_ID = os.getenv("TG_API_ID", "")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION_NAME = os.getenv("TG_SESSION_NAME", str(DATA_DIR / "vexa_telegram"))
TG_NEWS_CHANNEL_ID = os.getenv("TG_NEWS_CHANNEL_ID", "-1003883009617")
TG_SOURCE_CHANNELS = [
    int(x) for x in env_list("TG_SOURCE_CHANNELS", [])
    if x.lstrip("-").isdigit()
]
TG_ENABLED = bool(TG_API_ID and TG_API_HASH and TG_SOURCE_CHANNELS)
TG_QR_LOGIN = env_bool("TG_QR_LOGIN", True)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_BOT_CHAT_ID = os.getenv("TG_BOT_CHAT_ID", "")
SOCIAL_TELEGRAM_ENABLED = bool(TG_BOT_TOKEN and TG_BOT_CHAT_ID)

AXELCHAT_SESSIONS_DIR = Path(
    os.getenv(
        "AXELCHAT_SESSIONS_DIR",
        r"C:Usersserg9OneDriveДокументыAxelChatoutputsessions",
    )
)

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN", "").removeprefix("oauth:")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", os.getenv("TWITCH_USER", ""))

QUEUE_MAX_SIZE = env_int("VEXA_QUEUE_MAX_SIZE", 200)
QUEUE_NORMAL_TTL = env_float("VEXA_QUEUE_NORMAL_TTL", 45.0)
QUEUE_HIGH_TTL = env_float("VEXA_QUEUE_HIGH_TTL", 120.0)

ALLOW_AI_MODERATION = env_bool("ALLOW_AI_MODERATION", False)
MODERATION_MIN_CONFIDENCE = env_float("MODERATION_MIN_CONFIDENCE", 0.95)
