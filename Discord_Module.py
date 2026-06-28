import discord
from discord.ext import commands
import torch
import os
import asyncio
import time
from faster_whisper import WhisperModel

# 1. Настройка Silero (Голос) и Whisper (Слух)
# Используем CUDA для мгновенного распознавания на твоей RTX 3060
device = "cuda" if torch.cuda.is_available() else "cpu"
torch.set_num_threads(4)

# Загрузка голоса Silero
local_file = 'v5_ru.pt' 
if not os.path.isfile(local_file):
    import torch.hub
    print("📥 Скачиваю модель голоса Silero...")
    torch.hub.download_url_to_file('https://models.silero.ai', local_file)

# Инициализация моделей
try:
    tts_model = torch.package.PackageImporter(local_file).load_pickle("tts_models", "model")
    # УСТАНОВЛЕНО: Модель 'base' для высокой точности распознавания
    stt_model = WhisperModel("base", device=device, compute_type="float16" if device=="cuda" else "int8")
    print(f"👂 Whisper 'base' загружен на {device}")
except Exception as e:
    print(f"❌ Ошибка загрузки моделей (Голос/Слух): {e}")

# 2. Настройка бота Discord
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix="!", intents=intents)

class VexaVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.speaker = 'baya'
        self.sample_rate = 48000
        self.mood = 50  # Нейтральное настроение (0-100)
        self.log_file = "logs/full_dialogs.txt"

    def log_dialog(self, author, message, response):
        """Полный лог диалога без сокращений в файл"""
        if not os.path.exists("logs"): os.makedirs("logs")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = (
            f"[{timestamp}] [MOOD: {self.mood}]\n"
            f"ЗРИТЕЛЬ ({author}): {message}\n"
            f"ВЕКСА: {response}\n"
            f"{'='*40}\n"
        )
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

    @commands.command(name="зайди")
    async def join(self, ctx):
        """Команда захода в голосовой канал"""
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            vc = await channel.connect()
            self.bot.loop.create_task(self.stay_active(vc))
            await ctx.send(f"✅ Векса в канале: **{channel.name}**. Слушаю в режиме 'base'.")
        else:
            await ctx.send("⚠️ Зайди в голосовой канал, чтобы я могла тебя слышать!")

    async def stay_active(self, vc):
        """Поддержание активности в войсе (Анти-кик)"""
        while vc.is_connected():
            if not vc.is_playing():
                try:
                    # Проигрываем тишину для обхода ограничений Discord
                    vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source="silence.mp3"))
                except: pass
            await asyncio.sleep(20)

    def generate_audio(self, text, file_path="output.wav"):
        """Превращение текста в .wav через Silero"""
        tts_model.to_path(file_path, text=text, speaker=self.speaker, sample_rate=self.sample_rate)
        return file_path

    async def transcribe_voice(self, audio_path):
        """Распознавание речи из аудио-файла через Whisper base"""
        segments, _ = stt_model.transcribe(audio_path, beam_size=5, language="ru")
        text = "".join()
        return text.strip()

    def update_mood(self, change):
        """Изменение настроения Вексы (влияет на манеру ответов)"""
        self.mood = max(0, min(100, self.mood + change))
        print(f"🎭 [MOOD UPDATE] Новое настроение: {self.mood}")

# Инициализация модуля
async def init_discord_commands():
    if not bot.get_cog("VexaVoice"):
        await bot.add_cog(VexaVoice(bot))
        print("✅ Модуль VexaVoice (Whisper base + Mood) готов!")
