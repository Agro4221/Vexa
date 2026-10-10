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


def _check_ollama() -> list[Check]:
    """Verify that the configured local LLM service and model are actually usable."""
    if config.LLM_PROVIDER != "ollama":
        return []

    try:
        import requests

        response = requests.get(
            f"{config.OLLAMA_URL}/api/tags",
            timeout=3,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("models", []) if isinstance(payload, dict) else []
        names = [
            str(item.get("name", "")).strip()
            for item in items
            if isinstance(item, dict) and item.get("name")
        ]
    except Exception as exc:
        return [
            Check(
                "Ollama API",
                False,
                f"unreachable ({type(exc).__name__}); start Ollama and verify OLLAMA_URL",
                True,
            ),
            Check(
                "Ollama model availability",
                False,
                "not checked because the API is unavailable",
                True,
            ),
        ]

    api_check = Check(
        "Ollama API",
        True,
        "reachable",
        True,
    )
    if not names:
        model_check = Check(
            "Ollama model availability",
            False,
            "no models installed; use 'ollama pull <model>'",
            True,
        )
    elif config.LLM_MODEL:
        requested = config.LLM_MODEL.strip().lower()
        found = any(
            name.lower() == requested
            or (":" not in requested and name.lower().startswith(requested + ":"))
            for name in names
        )
        model_check = Check(
            "Ollama model availability",
            found,
            "configured model is installed"
            if found
            else f"configured model '{config.LLM_MODEL}' not found; check VEXA_MODEL",
            True,
        )
    elif not config.OLLAMA_AUTO_SELECT_MODEL:
        model_check = Check(
            "Ollama model availability",
            False,
            "set VEXA_MODEL or enable OLLAMA_AUTO_SELECT_MODEL",
            True,
        )
    else:
        model_check = Check(
            "Ollama model availability",
            True,
            f"{len(names)} installed model(s); runtime auto-selection is enabled",
            True,
        )

    return [api_check, model_check]


def run_checks() -> list[Check]:
    checks = _check_ollama() + [
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


def format_report(checks: list[Check]) -> str:
    """Format diagnostics for terminal use without exposing secret values."""
    lines = ["Vexa Health Check", "=" * 18]
    passed = 0
    warnings = 0
    critical_failures = 0

    for check in checks:
        if check.ok:
            status = "OK"
            passed += 1
        elif check.critical:
            status = "FAIL"
            critical_failures += 1
        else:
            status = "WARN"
            warnings += 1
        lines.append(f"[{status}] {check.name}: {check.detail}")

    lines.append("")
    lines.append(
        f"Summary: {passed}/{len(checks)} passed; "
        f"{warnings} warning(s); {critical_failures} critical failure(s)."
    )
    if critical_failures:
        lines.append("Result: NOT READY — fix critical failures before starting.")
    else:
        lines.append("Result: READY TO START — review warnings for optional features.")
    return "\n".join(lines)


def main() -> int:
    checks = run_checks()
    print(format_report(checks))
    return int(any(not check.ok and check.critical for check in checks))


if __name__ == "__main__":
    raise SystemExit(main())
