from __future__

import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import config


@dataclass(frozen=True)
class AttentionDecision:
    priority: int
    ttl: float
    reason: str


class AttentionManager:
    """Ranks incoming events and prevents one source from monopolizing attention."""

    def __init__(self) -> None:
        self._last_by_key: dict[str, float] = defaultdict(float)

    def classify(self, event: dict[str, Any]) -> AttentionDecision:
        message = str(event.get("message", "")).strip()
        service = str(event.get("service", "unknown")).lower()
        author = str(event.get("author", "unknown")).lower()
        lowered = message.lower()

        if event.get("priority") is not None:
            priority = max(0, min(3, int(event["priority"])))
            reason = "explicit"
        elif event.get("is_donate") or any(k in lowered for k in ("донат", "donate", "donationalerts", "donatepay")):
            priority, reason = 0, "donation"
        elif any(k in lowered for k in ("векса", "vexa", "мия", "мию")):
            priority, reason = 1, "direct_mention"
        elif service == "discord_voice":
            priority, reason = 1, "voice"
        elif service in {"twitch", "youtube", "vk", "axelchat"}:
            priority, reason = 2, "live_chat"
        else:
            priority, reason = 3, "background"

        return AttentionDecision(
            priority=priority,
            ttl=config.QUEUE_HIGH_TTL if priority <= 1 else config.QUEUE_NORMAL_TTL,
            reason=reason,
        )

    def should_accept(self, event: dict[str, Any]) -> bool:
        decision = self.classify(event)
        message = str(event.get("message", "")).strip().lower()
        key = f"{event.get('service','unknown')}:{event.get('author','unknown')}:{message[:120]}"
        now = time.monotonic()
        previous = self._last_by_key.get(key, 0.0)
        if decision.priority > 1 and now - previous < config.ATTENTION_COOLDOWN_SECONDS:
            return False
        self._last_by_key[key] = now
        return True

    def annotate(self, event: dict[str, Any]) -> dict[str, Any]:
        result = dict(event)
        decision = self.classify(result)
        result["priority"] = decision.priority
        result["ttl"] = decision.ttl
        result["attention_reason"] = decision.reason
        result.setdefault("timestamp", time.time())
        return result


attention = AttentionManager()
