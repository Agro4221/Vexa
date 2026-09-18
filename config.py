from __future__

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # optional for static tooling/tests
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
    if value is None or not value.strip():
        return default
    try:
        return int(value)
    except ValueError:
        return default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or not value.strip():
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


def env_path(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    return Path(raw).expanduser() if raw else default


DATA_DIR = env_path("VEXA_DATA_DIR", APP_ROOT / "data")
LOG_DIR = env_path("VEXA_LOG_DIR", DATA_DIR / "logs")
VISION_DIR = env_path("VEXA_VISION_DIR", DATA_DIR / "vision")
AUDIO_DIR = env_path("VEXA_AUDIO_DIR", DATA_DIR / "audio")
DB_PATH = env_path("VEXA_DB_PATH", DATA_DIR / "streamer_brain.db")
VTS_TOKEN_PATH = env_path("VTS_TOKEN_PATH", APP_ROOT / "vts_token.txt")

for _path in (DATA_DIR, LOG_DIR, VISION_DIR, AUDIO_DIR):
    _path.mkdir(parents=True, exist_ok=True)

# LLM configuration: deliberately model-agnostic. Leave VEXA_MODEL empty to
# auto-select a locally installed Ollama model.
LLM_PROVIDER = os.getenv("VEXA_LLM_PROVIDER", "ollama").strip().lower()
LLM_MODEL = os.getenv("VEXA_MODEL", os.getenv("LLM_MODEL", "")).strip()
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_TIMEOUT = env_float("OLLAMA_TIMEOUT", 45.0)
OLLAMA_AUTO_SELECT_MODEL = env_bool("OLLAMA_AUTO_SELECT_MODEL", True)
OLLAMA_MODEL_FALLBACK = os.getenv("OLLAMA_MODEL_FALLBACK", "").strip()
MAX_HISTORY = max(2, env_int("MAX_HISTORY", 12))
MAX_CONTEXT_CHARS = max(500, env_int("MAX_CONTEXT_CHARS", 7000))
USE_WEB_SEARCH = env_bool("USE_WEB_SEARCH", True)
USE_STRUCTURED_OUTPUT = env_bool("USE_STRUCTURED_OUTPUT", True)

SEARCH_TRIGGERS = env_list(
    "SEARCH_TRIGGERS",
    ["найди", "погугли", "загугли", "кто такой", "что такое", "как найти", "интернет"],
)

# Persona defaults preserve the source project idea while keeping identity data
# out of the core implementation where possible.
VEXA_NAME = os.getenv("VEXA_NAME", "Vexa")
VEXA_AGE = env_int("VEXA_AGE", 25)
VEXA_BIRTHDAY = os.getenv("VEXA_BIRTHDAY", "04.02.2026")
VEXA_STYLE = os.getenv(
    "VEXA_STYLE",
    "живая, дерзкая, немного пошлая, но без контента, который создаёт риск блокировки платформы",
)

VOICE_MODEL_PATH = env_path("VOICE_MODEL_PATH", APP_ROOT / "v5_ru.pt")
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
LOCAL_MIC_ENABLED = env_bool("LOCAL_MIC_ENABLED", False)

USE_VISION = env_bool("USE_VISION", True)
VISION_MODEL_ID = os.getenv("VISION_MODEL_ID", "vikhyatk/moondream2")
VISION_MODEL_REVISION = os.getenv("VISION_MODEL_REVISION", "2024-08-26")
VISION_DEVICE = os.getenv("VISION_DEVICE", "cpu")
VISION_MAX_IMAGE_WIDTH = env_int("VISION_MAX_IMAGE_WIDTH", 1920)
VISION_ENABLE_TRANSFORMERS_COMPAT_PATCH = env_bool(
    "VISION_ENABLE_TRANSFORMERS_COMPAT_PATCH", True
)
VISION_INTERVAL = max(1, env_int("VISION_INTERVAL", 10))
VISION_SAVE_LAST_ONLY = env_bool("VISION_SAVE_LAST_ONLY", True)
VISION_PROMPT = os.getenv(
    "VISION_PROMPT",
    "Describe the screen briefly. Mention only visible, relevant facts and avoid guessing.",
)
VISION_AUTONOMOUS = env_bool("VISION_AUTONOMOUS", False)

VTS_ENABLED = env_bool("VTS_ENABLED", True)
VTS_HOST = os.getenv("VTS_HOST", "localhost")
VTS_PORT = env_int("VTS_PORT", 8001)
VTS_PLUGIN_NAME = os.getenv("VTS_PLUGIN_NAME", "Vexa_AI")
VTS_PLUGIN_DEVELOPER = os.getenv("VTS_PLUGIN_DEVELOPER", "Vexa")
VTS_HOTKEY_JOY = os.getenv("VTS_HOTKEY_JOY", "Joy")
VTS_HOTKEY_ANGRY = os.getenv("VTS_HOTKEY_ANGRY", "Angry")
VTS_HOTKEY_SURPRISE = os.getenv("VTS_HOTKEY_SURPRISE", "Surprise")
VTS_IDLE_MOTION = env_bool("VTS_IDLE_MOTION", True)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DISCORD_ENABLED = env_bool("DISCORD_ENABLED", bool(DISCORD_TOKEN))
DISCORD_PREFIX = os.getenv("DISCORD_PREFIX", "!")
DISCORD_VOICE_REPLY = env_bool("DISCORD_VOICE_REPLY", True)
DISCORD_RECEIVE_VOICE = env_bool("DISCORD_RECEIVE_VOICE", True)
DISCORD_DEFAULT_GUILD_ID = env_int("DISCORD_DEFAULT_GUILD_ID", 0)
DISCORD_MIN_AUDIO_BYTES = env_int("DISCORD_MIN_AUDIO_BYTES", 24000)
DISCORD_MAX_AUDIO_BYTES = env_int("DISCORD_MAX_AUDIO_BYTES", 1920000)

TG_API_ID = os.getenv("TG_API_ID", "")
TG_API_HASH = os.getenv("TG_API_HASH", "")
TG_SESSION_NAME = os.getenv("TG_SESSION_NAME", str(DATA_DIR / "vexa_telegram"))
TG_NEWS_CHANNEL_ID = os.getenv("TG_NEWS_CHANNEL_ID", "")
TG_SOURCE_CHANNELS = [
    int(x) for x in env_list("TG_SOURCE_CHANNELS", []) if x.lstrip("-").isdigit()
]
TG_ENABLED = env_bool("TG_ENABLED", bool(TG_API_ID and TG_API_HASH and TG_SOURCE_CHANNELS and TG_NEWS_CHANNEL_ID))
TG_QR_LOGIN = env_bool("TG_QR_LOGIN", True)

TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_BOT_CHAT_ID = os.getenv("TG_BOT_CHAT_ID", "")
SOCIAL_TELEGRAM_ENABLED = env_bool("SOCIAL_TELEGRAM_ENABLED", bool(TG_BOT_TOKEN and TG_BOT_CHAT_ID))

_default_axelchat = (
    Path.home() / "OneDrive" / "Документы" / "AxelChat" / "output" / "sessions"
)
AXELCHAT_SESSIONS_DIR = env_path("AXELCHAT_SESSIONS_DIR", _default_axelchat)
AXELCHAT_ENABLED = env_bool("AXELCHAT_ENABLED", True)

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID", "")
TWITCH_TOKEN = os.getenv("TWITCH_TOKEN", "").removeprefix("oauth:")
TWITCH_CHANNEL = os.getenv("TWITCH_CHANNEL", os.getenv("TWITCH_USER", "")).lstrip("#")
TWITCH_BOT_USERNAME = os.getenv("TWITCH_BOT_USERNAME", TWITCH_CHANNEL)
TWITCH_ENABLED = env_bool("TWITCH_ENABLED", bool(TWITCH_CLIENT_ID and TWITCH_TOKEN and TWITCH_CHANNEL))

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID", "")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET", "")
YT_PROJECT_ID = os.getenv("YT_PROJECT_ID", "")
YT_CHANNEL_ID = os.getenv("YT_CHANNEL_ID", "")
YT_CLIENT_SECRET_FILE = env_path("YT_CLIENT_SECRET_FILE", APP_ROOT / "client_secret.json")
YT_TOKEN_FILE = env_path("YT_TOKEN_FILE", DATA_DIR / "youtube_token.json")
YT_LIVE_CHAT_ID = os.getenv("YT_LIVE_CHAT_ID", "")
YT_ENABLED = env_bool("YT_ENABLED", bool(YT_CLIENT_ID and YT_CLIENT_SECRET))
YT_POLLING_DEFAULT_SECONDS = max(1.0, env_float("YT_POLLING_DEFAULT_SECONDS", 5.0))

VK_ENABLED = env_bool("VK_ENABLED", False)
VK_SERVICE_KEY = os.getenv("VK_SERVICE_KEY", "")
VK_PROTECTED_KEY = os.getenv("VK_PROTECTED_KEY", "")
VK_API_BASE_URL = os.getenv("VK_API_BASE_URL", "").rstrip("/")
VK_MODERATION_PATH = os.getenv("VK_MODERATION_PATH", "")

OBS_ENABLED = env_bool("OBS_ENABLED", False)
OBS_HOST = os.getenv("OBS_HOST", "127.0.0.1")
OBS_PORT = env_int("OBS_PORT", 4455)
OBS_PASSWORD = os.getenv("OBS_PASSWORD", "")
OBS_SCENE_LIVE = os.getenv("OBS_SCENE_LIVE", "")
OBS_SCENE_BRB = os.getenv("OBS_SCENE_BRB", "")

QUEUE_MAX_SIZE = max(10, env_int("VEXA_QUEUE_MAX_SIZE", 200))
QUEUE_NORMAL_TTL = env_float("VEXA_QUEUE_NORMAL_TTL", 45.0)
QUEUE_HIGH_TTL = env_float("VEXA_QUEUE_HIGH_TTL", 120.0)
ATTENTION_COOLDOWN_SECONDS = env_float("ATTENTION_COOLDOWN_SECONDS", 2.0)
MOOD_MIN = 0
MOOD_MAX = 100
MOOD_DECAY_PER_MINUTE = env_float("MOOD_DECAY_PER_MINUTE", 1.0)

ALLOW_AI_MODERATION = env_bool("ALLOW_AI_MODERATION", False)
MODERATION_MIN_CONFIDENCE = env_float("MODERATION_MIN_CONFIDENCE", 0.95)
