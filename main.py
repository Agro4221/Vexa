from __future__ import annotations

import asyncio
import contextlib
import signal
import time
from typing import Any

import config
import ears
from Action_Manager import apply_actions, parse_actions
from Announcement_Manager import AnnouncementManager
from Attention_Manager import attention
from Autonomy_Manager import AutonomyManager
from Core_Brain import ai_brain
from Data_Base import memory
from Dialog_Logger import log_dialog
from Event_Bus import EventBus
from Health_Check import run_checks
from logger import clear_old_data, log_event
from Memory_Core import vexa_memory
from Moderation_Manager import ModerationRequest, moderation
from PicoClaw_Manager import skills
from Runtime_Control import GenerationCancelled, control
from Stream_Manager import stream_manager
from Supervisor import Supervisor
from TTS_Manager import tts_manager
from Vexa_State import state
from VTS_Module import vexa_vts
from Vision_Module import vexa_eyes

try:
    from watchdog.observers import Observer
except ImportError:
    Observer = None

try:
    from AxelChat_Watcher import AxelChatHandler
except ImportError as exc:
    AxelChatHandler = None
    AXELCHAT_IMPORT_ERROR = exc
else:
    AXELCHAT_IMPORT_ERROR = None

try:
    from Discord_Module import bot, init_discord_commands
except Exception as exc:
    bot = None
    init_discord_commands = None
    DISCORD_IMPORT_ERROR = exc
else:
    DISCORD_IMPORT_ERROR = None

bus = EventBus()
supervisor = Supervisor()
shutdown_event = asyncio.Event()
observer = None
announcements = AnnouncementManager(lambda: bot)
autonomy = AutonomyManager(lambda event: enqueue_event(event))


def enqueue_event(event: dict[str, Any]) -> bool:
    try:
        payload = dict(event)
        if payload.get("kind") == "system":
            autonomy.observe_event(payload)
            loop = asyncio.get_running_loop()
            loop.create_task(announcements.handle_event(payload))
            return False
        payload = attention.annotate(payload)
        if not attention.should_accept(payload):
            return False
        return bus.submit(payload)
    except RuntimeError:
        log_event("QUEUE_ERR", "Событие получено вне активного runtime loop.")
        return False
    except Exception as exc:
        log_event("QUEUE_ERR", f"Не удалось поставить событие в очередь: {exc}")
        return False


async def _reply_to_discord_text(text: str, event: dict[str, Any]) -> None:
    if bot is None:
        return
    channel_id = event.get("channel_id")
    if not channel_id:
        return
    try:
        channel = bot.get_channel(int(channel_id))
        if channel is not None:
            await channel.send(text)
    except Exception as exc:
        log_event("DISCORD_ERR", f"Ответ в Discord не отправлен: {exc}")


def _queue_voice_reply(text: str, event: dict[str, Any], priority: int) -> None:
    guild_id = event.get("guild_id")
    tts_manager.enqueue(
        text=text,
        guild_id=int(guild_id) if guild_id else None,
        priority=priority,
    )


async def process_event(event: dict[str, Any]) -> None:
    author = str(event.get("author", "Зритель"))
    message = str(event.get("message", "")).strip()
    service = str(event.get("service", "unknown")).lower()
    platform = str(event.get("platform", service)).lower()
    kind = str(event.get("kind", "chat")).lower()
    user_id = str(event.get("user_id", event.get("author_id", "")))

    if not message or kind == "system":
        return

    state.mark_activity(platform, author)
    priority = int(event.get("priority", 3))
    if event.get("is_donate") or priority == 0:
        state.mark_donation()
    else:
        state.apply_chat_signal(message)

    if config.USE_VISION and any(
        word in message.lower()
        for word in ("смотри", "глянь", "видишь", "экран", "что там")
    ):
        try:
            await asyncio.wait_for(
                vexa_eyes.analyze_screen(config.VISION_PROMPT),
                timeout=config.VISION_TIMEOUT,
            )
        except asyncio.TimeoutError:
            log_event(
                "EYES_ERR",
                "Анализ зрения превысил таймаут; обработка чата продолжается.",
            )

    snapshot = state.snapshot()
    past = await asyncio.to_thread(
        vexa_memory.get_recent_context,
        message,
        4,
        platform
        if platform
        in {
            "discord",
            "discord_voice",
            "twitch",
            "youtube",
            "vk",
            "telegram_chat",
            "telegram_news",
        }
        else None,
        user_id,
    )
    nl = chr(10)
    context = nl.join(
        [
            f"Описание экрана: {snapshot.last_vision_description}",
            f"Платформа: {platform}",
            f"Никнейм: {author}",
            f"Это донат: {'да' if event.get('is_donate') else 'нет'}",
            f"Память: {past}",
        ]
    )

    try:
        result = await ai_brain.get_response(
            author,
            message,
            platform,
            context,
            snapshot.mood,
        )
    except GenerationCancelled:
        log_event(
            "CONTROL",
            f"Обработка сообщения от {author} отменена оператором.",
        )
        return
    except Exception as exc:
        log_event("WORKER_ERR", f"Мозг не обработал событие: {exc}")
        return

    parsed = parse_actions(result.get("reply", ""))
    emotion = str(result.get("emotion", "neutral"))
    if emotion in {"joy", "angry", "surprise"} and not parsed.emotion:
        parsed = parsed.__class__(
            parsed.text,
            emotion,
            parsed.moderation_target,
            parsed.moderation_action,
            parsed.moderation_duration,
        )

    moderation_data = result.get("moderation") or {}
    target = str(moderation_data.get("target", "")).strip()
    action = str(moderation_data.get("action", "none"))
    duration = moderation_data.get("duration_seconds")
    reason = str(
        moderation_data.get("reason", "AI moderation")
    ).strip() or "AI moderation"

    if target and not parsed.moderation_target:
        parsed = parsed.__class__(
            parsed.text,
            parsed.emotion,
            target[:200],
            action.removeprefix("suggest_"),
            duration,
        )

    moderation_target = parsed.moderation_target
    if (
        moderation_target
        and moderation_target.casefold() != author.casefold()
    ):
        log_event(
            "MODERATION",
            f"Отклонена подозрительная цель: {moderation_target!r} != {author!r}",
        )
        moderation_target = None

    await apply_actions(parsed, vexa_vts)

    if (
        moderation_target
        and user_id
        and platform in {"twitch", "youtube", "vk"}
    ):
        requested_action = parsed.moderation_action or (
            "timeout" if action == "suggest_timeout" else "ban"
        )
        request = ModerationRequest(
            platform=platform,
            user_id=user_id,
            action=requested_action,
            duration_seconds=(
                int(duration)
                if isinstance(duration, (int, float)) and duration > 0
                else parsed.moderation_duration
            ),
            reason=reason,
            message_id=str(event.get("message_id", "")),
        )
        await moderation.execute(request)

    state_snapshot = state.snapshot()
    if parsed.text:
        await asyncio.to_thread(
            memory.add_event,
            platform,
            author,
            message,
            parsed.text,
            state_snapshot.mood,
            state_snapshot.last_vision_path,
            user_id,
            str(event.get("message_id", "")),
            str(event.get("session_id", "")),
            str(event.get("source_time", "")),
        )

    log_dialog(
        platform=platform,
        author=author,
        author_id=user_id,
        message=message,
        response=parsed.text,
        emotion=parsed.emotion or emotion,
        moderation={
            "action": action,
            "target": moderation_target or "",
            "duration_seconds": duration,
            "reason": reason,
        },
    )

    if not parsed.text:
        return

    if platform in {"discord_voice", "donation"}:
        _queue_voice_reply(
            parsed.text,
            event,
            priority,
        )
    elif platform == "discord":
        await _reply_to_discord_text(
            parsed.text,
            event,
        )
    elif platform == "twitch":
        await stream_manager.send_twitch_message(parsed.text)
    elif platform == "youtube":
        await stream_manager.send_youtube_message(parsed.text)
    elif platform == "vk":
        await stream_manager.send_vk_message(parsed.text)


async def worker() -> None:
    log_event("SYSTEM", "Главный worker Vexa запущен.")
    while not shutdown_event.is_set():
        try:
            event = await asyncio.wait_for(bus.get(), timeout=1)
        except asyncio.TimeoutError:
            continue
        try:
            await process_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event("WORKER_ERR", f"Ошибка обработки события: {exc}")


async def start_axelchat() -> None:
    global observer
    if not config.AXELCHAT_ENABLED:
        return
    if Observer is None:
        log_event("CHAT", "AxelChat отключён: watchdog не установлен.")
        return
    if AxelChatHandler is None:
        log_event(
            "CHAT",
            f"AxelChat watcher недоступен: {AXELCHAT_IMPORT_ERROR}",
        )
        return
    if not config.AXELCHAT_SESSIONS_DIR.exists():
        log_event(
            "CHAT",
            f"AxelChat путь не найден: {config.AXELCHAT_SESSIONS_DIR}",
        )
        return

    loop = asyncio.get_running_loop()
    handler = AxelChatHandler(enqueue_event, loop)
    observer = Observer()
    observer.schedule(
        handler,
        str(config.AXELCHAT_SESSIONS_DIR),
        recursive=True,
    )
    observer.start()
    handler.initial_scan(
        config.AXELCHAT_SESSIONS_DIR,
        emit_existing=False,
    )
    log_event("CHAT", "AxelChat Watcher запущен.")


async def run_twitch() -> None:
    from Twitch_Module import twitch_client

    twitch_client.event_callback = enqueue_event
    await twitch_client.connect()


async def run_youtube() -> None:
    from YouTube_Module import youtube_client

    youtube_client.event_callback = enqueue_event
    await youtube_client.run()


async def run_local_mic() -> None:
    if not config.LOCAL_MIC_ENABLED:
        return
    while not shutdown_event.is_set():
        try:
            text = await ears.listen()
            if text:
                enqueue_event(
                    {
                        "priority": 1,
                        "timestamp": time.time(),
                        "author": "local_microphone",
                        "user_id": "local_microphone",
                        "message": text,
                        "service": "local_mic",
                        "platform": "discord_voice",
                    }
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                "EARS_ERR",
                f"Локальный микрофон остановился: {exc}",
            )
            await asyncio.sleep(2)


async def run_obs() -> None:
    from OBS_Module import obs_controller

    await obs_controller.connect()
    await shutdown_event.wait()


async def run_telegram() -> None:
    from TG_Module import start_tg

    await start_tg()


async def run_discord() -> None:
    if not config.DISCORD_ENABLED:
        return
    if bot is None or init_discord_commands is None:
        raise RuntimeError(
            "Discord dependencies unavailable while DISCORD_ENABLED=true"
        )

    cog = await init_discord_commands(
        enqueue_event
    )
    if cog is not None:
        tts_manager.bind(cog.speak_text)

    await bot.start(
        config.DISCORD_TOKEN
    )


async def main() -> None:
    clear_old_data()
    skills.ensure_default()
    log_event(
        "SYSTEM",
        "Vexa boot sequence started.",
    )

    for check in run_checks():
        if not check.ok:
            log_event(
                "HEALTH",
                f"{check.name}: {check.detail}",
            )

    loop = asyncio.get_running_loop()
    for sig in (
        getattr(signal, "SIGINT", None),
        getattr(signal, "SIGTERM", None),
    ):
        if sig is not None:
            with contextlib.suppress(
                NotImplementedError,
                OSError,
            ):
                loop.add_signal_handler(
                    sig,
                    shutdown_event.set,
                )

    if config.VTS_ENABLED:
        await vexa_vts.connect()
        if config.VTS_IDLE_MOTION:
            supervisor.start(
                "vts-idle",
                vexa_vts.start_idle_motion,
                restart=True,
            )

    await start_axelchat()

    if config.DISCORD_ENABLED:
        supervisor.start(
            "discord",
            run_discord,
            restart=True,
        )
    if config.LOCAL_MIC_ENABLED:
        supervisor.start(
            "local-mic",
            run_local_mic,
            restart=True,
        )
    if config.TG_ENABLED:
        supervisor.start(
            "telegram",
            run_telegram,
            restart=True,
        )
    if config.TWITCH_ENABLED:
        supervisor.start(
            "twitch",
            run_twitch,
            restart=True,
        )
    if config.YT_ENABLED:
        supervisor.start(
            "youtube",
            run_youtube,
            restart=True,
        )
    if config.OBS_ENABLED:
        supervisor.start(
            "obs",
            run_obs,
            restart=True,
        )
    if (
        config.USE_VISION
        and config.VISION_AUTONOMOUS
    ):
        supervisor.start(
            "vision",
            vexa_eyes.autonomous_loop,
            restart=True,
        )
    if config.AUTONOMY_ENABLED:
        supervisor.start(
            "autonomy",
            autonomy.heartbeat,
            restart=True,
        )

    worker_task = asyncio.create_task(
        worker(),
        name="vexa:worker",
    )
    log_event(
        "SYSTEM",
        "Vexa runtime ready.",
    )

    try:
        await shutdown_event.wait()
    finally:
        control.stop_all()
        worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await worker_task
        await supervisor.stop()
        await tts_manager.stop()

        if observer is not None:
            observer.stop()
            observer.join(timeout=3)

        await vexa_vts.close()

        from Twitch_Module import twitch_client
        from YouTube_Module import youtube_client

        twitch_client.stop()
        youtube_client.stop()

        if bot is not None and not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
