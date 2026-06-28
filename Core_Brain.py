import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class StreamerAI:
    def __init__(self, model_name="shayzinasimulation/red-angel-8b-rede-uncensored-abliterated"):
        self.model_name = model_name
        self.url = "http://localhost:11434/api/generate"
        
        # Системный промпт (Личность Вексы)
        self.base_prompt = (
            "Ты — популярная стримерша Vexa 'Векса', тебе 25 лет, а день рождения '4 февраля, 2026' 04,02,2026."
            "Твой стиль общения: живой, дерзкий, немного пошлый - но не настолько что-бы получить из-за этого бан на Twitch/YouTube/VK Play Live, используешь молодежный сленг. "
            "Ты общаешься в Discord, Twitch, YouTube и VK Play. "
            "Если в контексте есть донат — благодари бурно. "
            "ВАЖНО: Ты можешь управлять своим телом и чатом с помощью команд в конце сообщения: "
            "[JOY] - если ты рада, [ANGRY] - если злишься, [SURPRISE] - если удивлена. "
            "[BAN: никнейм] - если кто-то ведет себя как урод, или байтит на что-то что может забанить каналы на Twitch, Youtube, VK Play Live. "
        )

    async def get_response(self, author, message, platform, context="", mood=50):
        # Адаптация личности под настроение
        mood_instruction = f"\nТвое текущее настроение: {mood}/100. "
        if mood < 30: mood_instruction += "Ты сейчас очень раздражена и дерзка. Можешь грубить."
        elif mood > 80: mood_instruction += "Ты в отличном настроении, флиртуй и шути больше."
        else: mood_instruction += "Ты в обычном, стабильном состоянии."

        full_prompt = (
            f"{self.base_prompt}{mood_instruction}\n"
            f"Контекст (что ты видишь и помнишь): {context}\n"
            f"Платформа: {platform}\n"
            f"Зритель {author} пишет: {message}\n"
            f"Твой ответ (1-3 предложения):"
        )
        
        payload = {
            "model": self.model_name,
            "prompt": full_prompt,
            "stream": False
        }

        try:
            response = requests.post(self.url, json=payload, timeout=15)
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Я... я чет засмотрелась на чат. Повтори?").strip()
            return "Мои микросхемы слегка перегрелись."
        except Exception as e:
            return f"Я временно в астрале! (Ошибка: {e})"

ai_brain = StreamerAI()
