from __future__ import annotations
import asyncio,signal,time
from pathlib import Path
from typing import Any
import config
from Action_Manager import apply_actions,parse_actions
from AxelChat_Watcher import AxelChatHandler
from Core_Brain import ai_brain
from Data_Base import memory
from Memory_Core import vexa_memory
from VTS_Module import vexa_vts
from Vision_Module import vexa_eyes
from logger import clear_old_data,log_event

try:
    from watchdog.observers import Observer
except ImportError: Observer=None
try:
    from Discord_Module import bot,init_discord_commands
except Exception as exc:
    bot=None; init_discord_commands=None; DISCORD_IMPORT_ERROR=exc
else: DISCORD_IMPORT_ERROR=None
try:
    from TG_Module import start_tg
except Exception as exc:
    start_tg=None; TG_IMPORT_ERROR=exc
else: TG_IMPORT_ERROR=None

task_queue:asyncio.PriorityQueue=asyncio.PriorityQueue(maxsize=config.QUEUE_MAX_SIZE)
_sequence=0
_shutdown=asyncio.Event()
_observer=None
_worker_task=None

def request_shutdown(): _shutdown.set()

def enqueue_event(event:dict[str,Any])->None:
    global _sequence
    priority=int(event.get("priority",3)); now=time.time(); ts=float(event.get("timestamp",now))
    ttl=config.QUEUE_HIGH_TTL if priority<=1 else config.QUEUE_NORMAL_TTL
    if now-ts>ttl: return
    if task_queue.full():
        log_event("QUEUE","Очередь переполнена; событие отброшено."); return
    _sequence+=1; task_queue.put_nowait((priority,_sequence,ts,event))

async def process_event(event):
    author=str(event.get("author","Зритель")); message=str(event.get("message","")); service=str(event.get("service","unknown"))
    if not message.strip(): return
    low=message.lower()
    if any(w in low for w in ("смотри","глянь","видишь","экран","что там")):
        await vexa_eyes.analyze_screen("Опиши самое важное, что сейчас происходит на экране стрима, коротко и без выдумок.")
    past=await asyncio.to_thread(vexa_memory.get_recent_context,message,3,service if service in {"discord_voice","twitch","youtube","vk"} else None)
    context=f"Описание экрана: {vexa_eyes.last_description}\nПамять: {past}"
    cog=bot.get_cog("VexaVoice") if bot else None
    mood=int(cog.mood) if cog else 50
    if int(event.get("priority",3))==0 and cog: cog.update_mood(10)
    result=await ai_brain.get_response(author,message,service,context,mood)
    em=result.get("emotion")
    actions=parse_actions(result.get("reply","")+(f" [{str(em).upper()}]" if em and em!="neutral" else ""))
    moderation=result.get("moderation") or {}
    if moderation.get("action")=="suggest_ban" and moderation.get("target"):
        actions=ParsedActions(actions.text,actions.emotion,str(moderation["target"])) if False else actions.__class__(actions.text,actions.emotion,str(moderation["target"]))
    await apply_actions(actions)
    if not actions.text: return
    current_mood=int(cog.mood) if cog else 50
    await asyncio.to_thread(memory.add_event,service,author,message,actions.text,current_mood,vexa_eyes.last_path or "")
    if cog and config.DISCORD_VOICE_REPLY:
        guild_id=event.get("guild_id") or (config.DISCORD_DEFAULT_GUILD_ID or None)
        await cog.speak_text(actions.text,guild_id=guild_id)

async def worker():
    log_event("SYSTEM","Главный worker Vexa запущен.")
    while not _shutdown.is_set():
        try: priority,seq,ts,event=await asyncio.wait_for(task_queue.get(),timeout=1)
        except asyncio.TimeoutError: continue
        try:
            ttl=config.QUEUE_HIGH_TTL if priority<=1 else config.QUEUE_NORMAL_TTL
            if time.time()-ts<=ttl: await process_event(event)
        except asyncio.CancelledError: raise
        except Exception as exc: log_event("WORKER_ERR",f"Ошибка обработки события: {exc}")
        finally: task_queue.task_done()

async def _start_axelchat():
    global _observer
    if Observer is None or not config.AXELCHAT_SESSIONS_DIR.exists(): return
    loop=asyncio.get_running_loop(); handler=AxelChatHandler(enqueue_event,loop)
    _observer=Observer(); _observer.schedule(handler,str(config.AXELCHAT_SESSIONS_DIR),recursive=True); _observer.start()
    handler.initial_scan(config.AXELCHAT_SESSIONS_DIR); log_event("CHAT","AxelChat Watcher запущен.")

async def main():
    global _worker_task
    clear_old_data()
    await vexa_vts.connect()
    if config.VTS_IDLE_MOTION: asyncio.create_task(vexa_vts.start_idle_motion())
    await _start_axelchat()
    if bot is not None and config.DISCORD_ENABLED and init_discord_commands:
        await init_discord_commands(enqueue_event); asyncio.create_task(bot.start(config.DISCORD_TOKEN))
    elif DISCORD_IMPORT_ERROR: log_event("DISCORD",f"Discord недоступен: {DISCORD_IMPORT_ERROR}")
    if config.TG_ENABLED and start_tg: asyncio.create_task(start_tg())
    elif TG_IMPORT_ERROR: log_event("TG",f"Telegram недоступен: {TG_IMPORT_ERROR}")
    _worker_task=asyncio.create_task(worker())
    log_event("SYSTEM",f"Vexa запущена: model={config.CURRENT_MODEL}")
    try:
        while not _shutdown.is_set(): await asyncio.sleep(1)
    finally:
        if _observer is not None: _observer.stop(); _observer.join(timeout=3)
        if _worker_task:
            _worker_task.cancel()
            try: await _worker_task
            except asyncio.CancelledError: pass
        if bot is not None and not bot.is_closed(): await bot.close()
        await vexa_vts.close()

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
