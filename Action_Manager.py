from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional
import config
from VTS_Module import vexa_vts
from logger import log_event

_EMOTION_TAG=re.compile(r"\[(JOY|ANGRY|SURPRISE)\]",re.I)
_BAN_TAG=re.compile(r"\[BAN:\s*([^\]]+)\]",re.I)

@dataclass(frozen=True)
class ParsedActions:
    text:str
    emotion:Optional[str]=None
    moderation_target:Optional[str]=None

def parse_actions(response_text:str)->ParsedActions:
    em=_EMOTION_TAG.search(response_text); ban=_BAN_TAG.search(response_text)
    text=_BAN_TAG.sub("",_EMOTION_TAG.sub("",response_text))
    text=re.sub(r"\s+"," ",text).strip()
    return ParsedActions(text,em.group(1).lower() if em else None,ban.group(1).strip() if ban else None)

async def apply_actions(actions:ParsedActions)->None:
    if actions.emotion: await vexa_vts.trigger_emotion(actions.emotion)
    if actions.moderation_target:
        log_event("MODERATION",f"AI предложила модерацию {actions.moderation_target}; автоматический бан заблокирован policy-слоем.")
