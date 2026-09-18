from __future__ import annotations
import asyncio,threading,time,wave
from collections import defaultdict
from typing import Any,Callable,Optional
import config,ears,voice
from logger import log_event

try:
    import discord
    from discord.ext import commands
except ImportError:
    discord=None; commands=None
try:
    from discord.ext import voice_recv
except ImportError:
    voice_recv=None

def _sink_listener():
    if voice_recv is not None: return voice_recv.AudioSink.listener()
    def decorator(fn): return fn
    return decorator

if commands is not None:
    intents=discord.Intents.default()
    intents.message_content=True; intents.voice_states=True
    bot=commands.Bot(command_prefix=config.DISCORD_PREFIX,intents=intents)
else: bot=None

class VexaReceiveSink(voice_recv.AudioSink if voice_recv is not None else object):
    def __init__(self,loop,on_phrase):
        if voice_recv is None: raise RuntimeError("discord-ext-voice-recv не установлен")
        super().__init__(); self.loop=loop; self.on_phrase=on_phrase; self.buffers=defaultdict(bytearray); self.lock=threading.Lock()
    def wants_opus(self): return False
    def write(self,user,data):
        if user is None or getattr(user,"bot",False): return
        pcm=getattr(data,"pcm",None)
        if not pcm: return
        uid=int(getattr(user,"id",0))
        with self.lock:
            buf=self.buffers[uid]; buf.extend(pcm)
            if len(buf)>config.DISCORD_MAX_AUDIO_BYTES: del buf[:len(buf)-config.DISCORD_MAX_AUDIO_BYTES]
    @_sink_listener()
    def on_voice_member_speaking_stop(self,member):
        if member is None or getattr(member,"bot",False): return
        uid=int(getattr(member,"id",0))
        with self.lock: pcm=bytes(self.buffers.pop(uid,b""))
        if len(pcm)<config.DISCORD_MIN_AUDIO_BYTES: return
        asyncio.run_coroutine_threadsafe(self.on_phrase(member,pcm),self.loop)
    def cleanup(self):
        with self.lock: self.buffers.clear()

class VexaVoice(commands.Cog if commands is not None else object):
    def __init__(self,bot_instance,event_callback=None):
        if commands is not None: super().__init__()
        self.bot=bot_instance; self.event_callback=event_callback; self.mood=50
        self.sinks={}; self.processing_voice=set(); self.play_locks=defaultdict(asyncio.Lock)
    def set_event_callback(self,callback): self.event_callback=callback
    def update_mood(self,change:int)->int:
        self.mood=max(0,min(100,self.mood+int(change))); log_event("MOOD",f"Новое настроение: {self.mood}"); return self.mood
    @commands.command(name="зайди")
    async def join(self,ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("⚠️ Зайди в голосовой канал, чтобы я могла тебя слышать."); return
        channel=ctx.author.voice.channel
        if ctx.voice_client:
            if ctx.voice_client.channel!=channel: await ctx.voice_client.move_to(channel)
            vc=ctx.voice_client
        else:
            vc=await channel.connect(cls=voice_recv.VoiceRecvClient) if voice_recv is not None else await channel.connect()
        await ctx.send(f"✅ Векса в канале: **{channel.name}**.")
        if config.DISCORD_RECEIVE_VOICE and voice_recv is not None: await self._start_receiving(vc,ctx.guild.id)
    @commands.command(name="слушай")
    async def listen(self,ctx):
        if not ctx.voice_client: await ctx.send("Я не в голосовом канале."); return
        if voice_recv is None: await ctx.send("Для приёма Discord-аудио нужен discord-ext-voice-recv."); return
        await self._start_receiving(ctx.voice_client,ctx.guild.id); await ctx.send("👂 Слушаю голос.")
    @commands.command(name="перестаньслушать")
    async def stop_listening(self,ctx):
        sink=self.sinks.pop(getattr(ctx.guild,"id",0),None)
        if ctx.voice_client and voice_recv is not None:
            try: ctx.voice_client.stop_listening()
            except Exception: pass
        if sink: sink.cleanup()
        await ctx.send("👂 Слух отключён.")
    @commands.command(name="выйди",aliases=["ливни","исчезни"])
    async def leave(self,ctx):
        gid=getattr(ctx.guild,"id",0); sink=self.sinks.pop(gid,None)
        if sink: sink.cleanup()
        if ctx.voice_client:
            try:
                if voice_recv is not None: ctx.voice_client.stop()
            except Exception: pass
            await ctx.voice_client.disconnect()
            await ctx.send("👋 Вышла из войса.")
    async def _start_receiving(self,vc,guild_id:int):
        if voice_recv is None: return
        old=self.sinks.pop(guild_id,None)
        if old: old.cleanup()
        sink=VexaReceiveSink(asyncio.get_running_loop(),self._on_voice_phrase)
        self.sinks[guild_id]=sink; vc.listen(sink)
        log_event("DISCORD",f"Приём голосового аудио включён для guild={guild_id}")
    async def _on_voice_phrase(self,member,pcm:bytes):
        guild_id=getattr(getattr(member,"guild",None),"id",0); user_id=int(getattr(member,"id",0)); key=(guild_id,user_id)
        if key in self.processing_voice: return
        self.processing_voice.add(key)
        path=config.AUDIO_DIR/f"discord_{guild_id}_{int(time.time()*1000)}.wav"
        try:
            with wave.open(str(path),"wb") as w:
                w.setnchannels(2); w.setsampwidth(2); w.setframerate(48000); w.writeframes(pcm)
            text=await asyncio.to_thread(ears.transcribe_file,path)
            if text and self.event_callback:
                result=self.event_callback({"priority":1,"timestamp":time.time(),"author":getattr(member,"display_name",getattr(member,"name","Discord user")),"message":text,"service":"discord_voice","guild_id":guild_id})
                if asyncio.iscoroutine(result): await result
        except Exception as exc:
            log_event("DISCORD_ERR",f"Voice phrase error: {exc}")
        finally:
            path.unlink(missing_ok=True); self.processing_voice.discard(key)
    async def speak_text(self,text:str,guild_id:Optional[int]=None):
        if not bot or not config.DISCORD_VOICE_REPLY: return
        targets=[]
        if guild_id is not None:
            guild=bot.get_guild(int(guild_id))
            if guild and guild.voice_client: targets=[guild.voice_client]
        else: targets=[vc for vc in bot.voice_clients if vc.is_connected()]
        if not targets: return
        audio_path=await voice.generate_audio_async(text)
        try:
            for vc in targets:
                if not vc.is_connected(): continue
                async with self.play_locks[int(vc.guild.id)]:
                    if vc.is_playing(): vc.stop()
                    done=asyncio.Event()
                    def after_playback(error):
                        if error: log_event("DISCORD_ERR",f"Playback error: {error}")
                        bot.loop.call_soon_threadsafe(done.set)
                    vc.play(discord.FFmpegPCMAudio(executable="ffmpeg",source=audio_path),after=after_playback)
                    await done.wait()
        finally: voice.cleanup_audio(audio_path)

if bot is not None:
    @bot.event
    async def on_ready(): log_event("DISCORD",f"Discord готов. Пользователь: {bot.user}")

async def init_discord_commands(event_callback=None):
    if bot is None: return None
    cog=bot.get_cog("VexaVoice")
    if cog is None: cog=VexaVoice(bot,event_callback)
    elif event_callback is not None: cog.set_event_callback(event_callback)
    if bot.get_cog("VexaVoice") is None: await bot.add_cog(cog)
    return cog
