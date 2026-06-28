import os
import hashlib
import asyncio
import qrcode # Если нет, выполни: pip install qrcode
from telethon import TelegramClient, events
from dotenv import load_dotenv

# Импорт твоих модулей
from Data_Base import memory
from Core_Brain import ai_brain

# 1. Загрузка конфигурации
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
NEWS_CHANNEL_ID = -1003883009617 
SOURCE_CHANNELS = [-1001983288930, -1001418440636]
ADS_WORDS = ["erid:", "реклама", "подпишись", "закажи", "скидка", "скачать", "купить", "акция"]

# 2. Инициализация клиента
client = TelegramClient('vexa_qr_session', API_ID, API_HASH)

async def news_handler(event):
    if not event.text: return
    if any(word in event.text.lower() for word in ADS_WORDS): return
    post_hash = hashlib.md5(event.text.encode()).hexdigest()
    if memory.is_duplicate(post_hash): return

    print(f"📰 TG: Найдена новость, делаю рерайт...")
    prompt = f"Перескажи кратко и дерзко (ты 25-летняя стримерша Векса): {event.text}"
    rewritten_text = await ai_brain.get_response("Система", prompt, "TG_Parser")

    try:
        if event.media: await client.send_file(NEWS_CHANNEL_ID, event.media, caption=rewritten_text)
        else: await client.send_message(NEWS_CHANNEL_ID, rewritten_text)
        memory.add_tg_post(post_hash)
        print("✅ TG: Опубликовано!")
    except Exception as e: print(f"❌ TG Ошибка: {e}")

async def start_tg():
    print("🚀 TG_Module: ЗАПУСК АВТОРИЗАЦИИ ЧЕРЕЗ QR-КОД...")
    await client.connect()

    if not await client.is_user_authorized():
        qr_login = await client.qr_login()
        print("\n" + "="*30)
        print("1. Зайди в Telegram на телефоне.")
        print("2. Настройки -> Устройства -> Подключить устройство.")
        print("3. ОТКРОЙ ЭТУ ССЫЛКУ И ОТСКАНЕРУЙ QR-КОД:")
        print(f"👉 {qr_login.url}")
        print("="*30 + "\n")

        # Ждем, пока пользователь отсканирует код
        try:
            await qr_login.wait()
            print("\n✅ ВЕКСА В TELEGRAM АВТОРИЗОВАНА ЧЕРЕЗ QR!")
        except Exception as e:
            print(f"❌ Ошибка при сканировании: {e}")
            return

    # Запуск парсера
    client.add_event_handler(news_handler, events.NewMessage(chats=SOURCE_CHANNELS))
    if __name__ == "__main__":
        print("📡 Парсер запущен. Слушаю каналы...")
        await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(start_tg())
