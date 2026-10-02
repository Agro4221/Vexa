from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any

import config


@dataclass(frozen=True)
class AttentionDecision:
    priority: int
    ttl: float
    reason: str


class AttentionManager:
    def __init__(self) -> None:
        self._last_by_key: dict[str, float] = defaultdict(float)
        self._background_events: dict[str, deque[float]] = defaultdict(
            lambda: deque(maxlen=100)
        )

    def classify(self, event: dict[str, Any]) -> AttentionDecision:
        message = str(event.get("message", "")).strip()
        platform = str(
            event.get("platform")
            or event.get("service")
            or "unknown"
        ).lower()
        lowered = message.lower()

        if event.get("priority") is not None:
            priority = max(
                0,
                min(3, int(event["priority"])),
            )
            reason = "explicit"
        elif event.get("is_donate") or any(
            marker in lowered
            for marker in (
                "донат",
                "donate",
                "donationalerts",
                "donatepay",
            )
        ):
            priority, reason = 0, "donation"
        elif any(
            marker in lowered
            for marker in ("векса", "vexa", "мия", "мию")
        ):
            priority, reason = 1, "direct_mention"
        elif platform == "discord_voice":
            priority, reason = 1, "voice"
        elif platform in {
            "discord",
            "twitch",
            "youtube",
            "vk",
            "axelchat",
        }:
            priority, reason = 2, "live_chat"
        else:
            priority, reason = 3, "background"

        return AttentionDecision(
            priority=priority,
            ttl=(
                config.QUEUE_HIGH_TTL
                if priority <= 1
                else config.QUEUE_NORMAL_TTL
            ),
            reason=reason,
        )

    def should_accept(self, event: dict[str, Any]) -> bool:
        decision = self.classify(event)
        platform = str(
            event.get("platform")
            or event.get("service")
            or "unknown"
        ).lower()
        author = str(
            event.get("user_id")
            or event.get("author_id")
            or event.get("author")
            or "unknown"
        ).strip().lower()
        message = str(
            event.get("message", "")
        ).strip().lower()

        key = f"{platform}:{author}:{message[:180]}"
        now = time.monotonic()
        previous = self._last_by_key.get(key, 0.0)

        if decision.priority > 1:
            if now - previous < config.ATTENTION_COOLDOWN_SECONDS:
                return False
            bucket = self._background_events[platform]
            one_minute_ago = now - 60.0
            while bucket and bucket[0] < one_minute_ago:
                bucket.popleft()
            if len(bucket) >= config.ATTENTION_BACKGROUND_MAX_PER_MINUTE:
                return False
            bucket.append(now)

        self._last_by_key[key] = now
        return True

    def annotate(self, event: dict[str, Any]) -> dict[str, Any]:
        result = dict(event)
        decision = self.classify(result)
        result["priority"] = decision.priority
        result["ttl"] = decision.ttl
        result["attention_reason"] = decision.reason
        result.setdefault(
            "timestamp",
            time.time(),
        )
        return result


attention = AttentionManager()