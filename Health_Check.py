from __future__ import annotations

import shutil
from dataclasses import dataclass

import config
import voice


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str
    critical: bool = False


def run_checks() -> list[Check]:
    checks = [
        Check(
            "LLM provider",
            config.LLM_PROVIDER == "ollama",
            f"provider={config.LLM_PROVIDER}",
            True,
        ),
        Check(
            "LLM model selection",
            bool(config.LLM_MODEL or config.OLLAMA_AUTO_SELECT_MODEL),
            "explicit model or runtime auto-selection",
            True,
        ),
        Check(
            "TTS model",
            config.VOICE_MODEL_PATH.exists() or config.VOICE_AUTO_DOWNLOAD,
            str(config.VOICE_MODEL_PATH),
            True,
        ),
        Check(
            "FFmpeg",
            shutil.which("ffmpeg") is not None,
            "ffmpeg executable in PATH",
            False,
        ),
        Check(
            "AxelChat path",
            (not config.AXELCHAT_ENABLED)
            or config.AXELCHAT_SESSIONS_DIR.exists(),
            str(config.AXELCHAT_SESSIONS_DIR),
            False,
        ),
        Check(
            "Discord config",
            (not config.DISCORD_ENABLED)
            or bool(config.DISCORD_TOKEN),
            "token configured"
            if config.DISCORD_TOKEN
            else "disabled",
            False,
        ),
        Check(
            "Telegram news config",
            (not config.TG_ENABLED)
            or bool(
                config.TG_SOURCE_CHANNELS
                and config.TG_NEWS_CHANNEL_ID
            ),
            "sources + destination configured",
            False,
        ),
        Check(
            "YouTube config",
            (not config.YT_ENABLED)
            or bool(
                config.YT_CLIENT_ID
                and config.YT_CLIENT_SECRET
            ),
            "OAuth client configured",
            False,
        ),
        Check(
            "Twitch moderation identity",
            (not config.TWITCH_ENABLED)
            or (not config.ALLOW_AI_MODERATION)
            or bool(config.TWITCH_MODERATOR_ID),
            "moderator user ID configured"
            if config.TWITCH_MODERATOR_ID
            else "add TWITCH_MODERATOR_ID before enabling AI moderation",
            False,
        ),
        Check(
            "VK moderation endpoint",
            (not config.VK_ENABLED)
            or (not config.ALLOW_AI_MODERATION)
            or bool(
                config.VK_SERVICE_KEY
                and config.VK_API_BASE_URL
                and config.VK_MODERATION_PATH
            ),
            "service key + endpoint configured",
            False,
        ),
        Check(
            "OBS config",
            (not config.OBS_ENABLED)
            or bool(config.OBS_PASSWORD or config.OBS_PORT),
            "OBS endpoint configured",
            False,
        ),
        Check(
            "Vision config",
            (not config.USE_VISION)
            or bool(config.VISION_MODEL_ID),
            config.VISION_MODEL_ID,
            False,
        ),
        Check(
            "TTS sample rate",
            8000 <= config.SAMPLE_RATE <= 96000,
            str(config.SAMPLE_RATE),
            True,
        ),
        Check(
            "FFmpeg helper",
            voice.ffmpeg_available()
            if config.DISCORD_ENABLED and config.DISCORD_VOICE_REPLY
            else True,
            "playback helper available"
            if voice.ffmpeg_available()
            else "ffmpeg unavailable",
            False,
        ),
    ]
    return checks


def main() -> int:
    return (
        1
        if any(
            (not check.ok) and check.critical
            for check in run_checks()
        )
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
