from __future__ import annotations
import requests
import config
from logger import log_event

class StreamManager:
    def __init__(self):
        self.twitch_client_id=config.TWITCH_CLIENT_ID
        self.twitch_token=config.TWITCH_TOKEN
        self.twitch_channel=config.TWITCH_CHANNEL

    def _twitch_headers(self):
        return {"Authorization":f"Bearer {self.twitch_token}","Client-Id":self.twitch_client_id}

    def _twitch_get_broadcaster_id(self):
        if not self.twitch_channel: raise RuntimeError("TWITCH_CHANNEL не задан")
        r=requests.get("https://api.twitch.tv/helix/users",headers=self._twitch_headers(),params={"login":self.twitch_channel},timeout=10)
        r.raise_for_status(); data=r.json().get("data",[])
        if not data: raise RuntimeError(f"Twitch channel не найден: {self.twitch_channel}")
        return str(data[0]["id"])

    def update_twitch(self,title,category_name=None):
        if not self.twitch_client_id or not self.twitch_token: return False
        payload={"title":title}
        if category_name:
            r=requests.get("https://api.twitch.tv/helix/search/categories",headers=self._twitch_headers(),params={"query":category_name},timeout=10)
            r.raise_for_status(); cats=r.json().get("data",[])
            if cats: payload["game_id"]=str(cats[0]["id"])
        r=requests.patch("https://api.twitch.tv/helix/channels",headers={**self._twitch_headers(),"Content-Type":"application/json"},params={"broadcaster_id":self._twitch_get_broadcaster_id()},json=payload,timeout=10)
        r.raise_for_status(); log_event("TWITCH",f"Название обновлено: {title}"); return True

    def update_youtube(self,*args,**kwargs):
        raise NotImplementedError("YouTube OAuth/liveBroadcast management пока не подключён.")

    def vk_moderate(self,*args,**kwargs):
        raise NotImplementedError("VK Play moderation API пока не подключён.")

    async def create_global_poll(self,question,options):
        log_event("STREAM",f"Global poll request: {question} -> {options}")
