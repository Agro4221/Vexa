from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import config
from Vexa_State import state
from logger import log_event

_EMOTION_TAG = re.compile(r"\[(JOY|ANGRY|SURPRISE)\]", re.I)
_BAN_TAG = re.compile(r"\[BAN:\s*([^\]]+)\]", re.I)
_MOOD_DELTAS = {"joy": 3, "angry": -3, "surprise": 1}


@dataclass(frozen=True)
class ParsedActions:
    text: str
    emotion: Optional[str] = None
    moderation_target: Optional[str] = None


def parse_actions(response_text: str) -> ParsedActions:
    emotion = _EMOTION_TAG.search(response_text)
    ban = _BAN_TAG.search(response_text)
    text = _BAN_TAG.sub("", _EMOTION_TAG.sub("", response_text))
    text = re.sub(r"\s+", " ", text).strip()
    return ParsedActions(text, emotion.group(1).lower() if emotion else None, ban.group(1).strip() if ban else None)


async def apply_actions(actions: ParsedActions, vts=None) -> None:
    if actions.emotion:
        state.change_mood(_MOOD_DELTAS.get(actions.emotion, 0))
        if vts is not None:
            await vts.trigger_emotion(actions.emotion)
    if actions.moderation_target:
        status = "разрешена" if config.ALLOW_AI_MODERATION else "отключена"
        log_event("MODERATION", f"AI предложила модерацию {actions.moderation_target}; автоматическая модерация {status}.")
