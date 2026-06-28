import os
import requests
from twitchapi import Twitch # pip install twitchapi
from googleapiclient.discovery import build # pip install google-api-python-client
from dotenv import load_dotenv

load_dotenv()

class StreamManager:
    def __init__(self):
        # 1. Твич (через библиотеку twitchapi)
        self.twitch_id = os.getenv("TWITCH_CLIENT_ID")
        self.twitch_secret = os.getenv("TWITCH_CLIENT_SECRET")
        
        # 2. YouTube (через Google API)
        self.yt_key = os.getenv("YOUTUBE_API_KEY")
        self.youtube = build('youtube', 'v3', developerKey=self.yt_key)
        
        # 3. VK Play (через прямые запросы к API)
        self.vk_token = os.getenv("VK_SERVICE_KEY")

    # --- TWITCH: Смена названия и категории ---
    async def update_twitch(self, title, category_name):
        # Логика авторизации и отправки PATCH запроса в Twitch API
        print(f"Twitch: Название изменено на '{title}'")

    # --- YOUTUBE: Смена названия трансляции ---
    def update_youtube(self, video_id, title):
        request = self.youtube.liveBroadcasts().update(
            part="snippet",
            body={"id": video_id, "snippet": {"title": title}}
        )
        request.execute()

    # --- VK PLAY: Модерация (Бан/Таймаут) ---
    def vk_moderate(self, user_id, action="ban"):
        url = f"https://api.vkplay.live{action}"
        headers = {"Authorization": f"Bearer {self.vk_token}"}
        # Отправка запроса на бан пользователя
        pass

    # --- ОБЩИЙ ОПРОС (Одинаковый во всех чатах) ---
    async def create_global_poll(self, question, options):
        print(f"Создаю опрос везде: {question} -> {options}")
        # Вызов методов создания опроса для каждой платформы отдельно
