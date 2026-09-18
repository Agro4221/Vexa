from __future__ import annotations

import shutil
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    critical: bool = False


def run_checks() -> list[Check]:
    return [
        Check("LLM provider", config.LLM_PROVIDER == "ollama", f"provider={config.LLM_PROVIDER}", True),
        Check(
            "LLM model selection",
            bool(config.LLM_MODEL or config.OLLAMA_AUTO_SELECT_MODEL),
            "configured or auto-select enabled",
            True,
        ),
        Check("TTS model", config.VOICE_MODEL_PATH.exists() or config.VOICE_AUTO_DOWNLOAD, str(config.VOICE_MODEL_PATH), True),
        Check("FFmpeg", shutil.which("ffmpeg") is not None, "ffmpeg in PATH", False),
        Check("AxelChat path", (not config.AXELCHAT_ENABLED) or config.AXELCHAT_SESSIONS_DIR.exists(), str(config.AXELCHAT_SESSIONS_DIR), False),
        Check("Discord config", (not config.DISCORD_ENABLED) or bool(config.DISCORD_TOKEN), "token configured" if config.DISCORD_TOKEN else "disabled", False),
        Check("Telegram news config", (not config.TG_ENABLED) or bool(config.TG_SOURCE_CHANNELS and config.TG_NEWS_CHANNEL_ID), "source + destination configured", False),
        Check("YouTube config", (not config.YT_ENABLED) or bool(config.YT_CLIENT_ID and config.YT_CLIENT_SECRET), "OAuth client configured", False),
        Check("OBS config", (not config.OBS_ENABLED) or bool(config.OBS_PASSWORD or config.OBS_PORT), "OBS endpoint configured", False),
        Check("Vision dependencies", (not config.USE_VISION) or bool(config.VISION_MODEL_ID), config.VISION_MODEL_ID, False),
    ]


def main() -> int:
    return 1 if any(not check.ok and check.critical for check in run_checks()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
