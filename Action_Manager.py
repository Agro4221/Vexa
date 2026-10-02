from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import config
from Vexa_State import state
from logger import log_event

_EMOTION_TAG = re.compile(r"\[(JOY|ANGRY|SURPRISE)\]", re.I)
_BAN_TAG = re.compile(r"\[BAN:\s*([^\]]+)\]", re.I)
_TIMEOUT_TAG = re.compile(r"\[TIMEOUT:\s*([^\]]+)\]", re.I)
_MOOD_DELTAS = {"joy": 3, "angry": -3, "surprise": 1}


@dataclass(frozen=True)
class ParsedActions:
    text: str
    emotion: Optional[str] = None
    moderation_target: Optional[str] = None
    moderation_action: Optional[str] = None
    moderation_duration: Optional[int] = None


def parse_actions(response_text: str) -> ParsedActions:
    emotion = _EMOTION_TAG.search(response_text)
    ban = _BAN_TAG.search(response_text)
    timeout = _TIMEOUT_TAG.search(response_text)
    text = _BAN_TAG.sub("", response_text)
    text = _TIMEOUT_TAG.sub("", text)
    text = _EMOTION_TAG.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    action = None
    target = None
    duration = None
    if ban:
        action = "ban"
        target = ban.group(1).strip()
    elif timeout:
        action = "timeout"
        target = timeout.group(1).strip()
        duration = 300
    return ParsedActions(
        text=text,
        emotion=emotion.group(1).lower() if emotion else None,
        moderation_target=target,
        moderation_action=action,
        moderation_duration=duration,
    )


async def apply_actions(actions: ParsedActions, vts=None) -> None:
    if actions.emotion:
        state.change_mood(_MOOD_DELTAS.get(actions.emotion, 0))
        if vts is not None:
            await vts.trigger_emotion(actions.emotion)
    if actions.moderation_target:
        status = "разрешена" if config.ALLOW_AI_MODERATION else "отключена"
        log_event(
            "MODERATION",
            f"AI предложила {actions.moderation_action} для {actions.moderation_target}; автоматическая модерация {status}.",
        )
