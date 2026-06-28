import asyncio
import os
import sys
import warnings
import discord
import re
from dotenv import load_dotenv
from watchdog.observers import Observer

warnings.filterwarnings("ignore", category=UserWarning, message="TypedStorage is deprecated")

# Импорт твоих модулей
from Data_Base import memory
from VTS_Module import vexa_vts
from text_utils import prepare_text_for_tts
from Core_Brain import ai_brain
from AxelChat_Watcher import AxelChatHandler
from Discord_Module import bot, init_discord_commands
from Vision_Module import vexa_eyes
from TG_Module import start_tg
from Memory_Core import vexa_memory

load_dotenv()

task_queue = asyncio.PriorityQueue()

async def process_actions(response_text):
    """Парсинг команд ИИ (Эмоции, Баны)"""
    # 1. Эмоции для VTube Studio
    if "[JOY]" in response_text: await vexa_vts.trigger_emotion("Joy")
    if "[ANGRY]" in response_text: await vexa_vts.trigger_emotion("Angry")
    if "[SURPRISE]" in response_text: await vexa_vts.trigger_emotion("Surprise")
    
    # 2. Модерация (Пример для бана)
    ban_match = re.search(r"\[BAN: (.*?)\]", response_text)
    if ban_match:
        target = ban_match.group(1)
        print(f"🔨 МОДЕРАЦИЯ: Векса забанила пользователя {target}")
        # Здесь будет вызов API Twitch/YouTube/VK (когда подключим токены модератора)

async def vexa_worker():
    """Главный цикл: Сознание Вексы"""
    print("🧠 Мозговой центр Вексы запущен...")
    voice_module = None
    
    while True:
        priority, timestamp, data = await task_queue.get()
        try:
            # Получаем текущее настроение из модуля Дискорда
            if not voice_module: voice_module = bot.get_cog("VexaVoice")
            current_mood = voice_module.mood if voice_module else 50

            author = data.get('author', 'Зритель')
            message = data.get('message', '')
            service = data.get('service', 'unknown')

            print(f" >>> [ПРИОРИТЕТ {priority}] Обработка: {author} ({service})")

            # Память + Зрение
            past_context = vexa_memory.get_recent_context(message)
            context = f"Вижу на экране: {vexa_eyes.last_description}. Воспоминания: {past_context}"
            
            # Генерация ответа
            response = await ai_brain.get_response(author, message, service, context, current_mood)
            
            # Исполнение действий (Эмоции/Баны)
            await process_actions(response)
            
            # Очистка текста от тегов для озвучки
            clean_text = re.sub(r"\[.*?\]", "", response).strip()
            
            # Логирование в файл без сокращений
            if voice_module: voice_module.log_dialog(author, message, response)
            
            # Озвучка
            if voice_module and clean_text:
                audio_path = voice_module.generate_audio(prepare_text_for_tts(clean_text))
                for vc in bot.voice_clients:
                    if vc.is_connected():
                        if vc.is_playing(): vc.stop()
                        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=audio_path))
            
            memory.add_event(service, author, message, response)

        except Exception as e:
            print(f"❌ Ошибка воркера: {e}")
        finally:
            task_queue.task_done()

async def main():
    print(f"--- 🚀 ЗАПУСК VEXA AI v2.0 (ПОЛНАЯ СБОРКА) ---")
    
    await vexa_vts.connect()
    
    asyncio.create_task(vexa_worker())
    asyncio.create_task(vexa_vts.start_idle_motion())
    asyncio.create_task(vexa_eyes.analyze_screen()) # Первый взгляд
    asyncio.create_task(start_tg())

    log_path = r"C:\Users\serg9\OneDrive\Документы\AxelChat\output\sessions"
    if os.path.exists(log_path):
        loop = asyncio.get_running_loop()
        event_handler = AxelChatHandler(task_queue, loop)
        observer = Observer()
        observer.schedule(event_handler, log_path, recursive=True)
        observer.start()
        print("👀 AxelChat Watcher запущен.")

    token = os.getenv("DISCORD_TOKEN")
    if token:
        await init_discord_commands()
        asyncio.run_coroutine_threadsafe(bot.start(token), asyncio.get_event_loop())

    print("✅ ВСЕ СИСТЕМЫ ОНЛАЙН! Векса готова.")
    while True: await asyncio.sleep(1)

if __name__ == "__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: sys.exit(0)
