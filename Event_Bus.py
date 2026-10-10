from __future__ import annotations
import asyncio
import heapq
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import config
from logger import log_event


@dataclass(order=True)
class _QueuedEvent:
    priority: int
    sequence: int
    timestamp: float = field(compare=False)
    ttl: float = field(compare=False)
    payload: dict[str, Any] = field(compare=False)


class EventBus:
    """Thread-safe bounded priority queue usable from sync callbacks and asyncio."""

    def __init__(self, max_size: int | None = None) -> None:
        self.max_size = max(1, max_size or config.QUEUE_MAX_SIZE)
        self._heap: list[_QueuedEvent] = []
        self._sequence = 0
        self._lock = threading.Lock()

    def submit(self, event: dict[str, Any]) -> bool:
        now = time.time()
        try:
            timestamp = float(event.get("timestamp", now))
            ttl = float(event.get("ttl", config.QUEUE_NORMAL_TTL))
        except (TypeError, ValueError, OverflowError):
            log_event("QUEUE", "Событие отброшено: некорректные timestamp/ttl.")
            return False

        if not (0 < ttl < float("inf")) or not (0 < timestamp < float("inf")):
            return False
        if timestamp > now + 60 or now - timestamp > ttl:
            return False

        raw_priority = event.get("priority", 3)
        try:
            priority = 3 if raw_priority is None else int(raw_priority)
        except (TypeError, ValueError, OverflowError):
            priority = 3

        with self._lock:
            self._sequence += 1
            item = _QueuedEvent(
                priority=max(0, min(3, priority)),
                sequence=self._sequence,
                timestamp=timestamp,
                ttl=ttl,
                payload=dict(event),
            )
            if len(self._heap) >= self.max_size:
                worst_index = max(
                    range(len(self._heap)),
                    key=lambda i: (self._heap[i].priority, self._heap[i].sequence),
                )
                worst = self._heap[worst_index]
                if item.priority >= worst.priority:
                    log_event("QUEUE", "Очередь переполнена; событие отброшено.")
                    return False
                self._heap[worst_index] = item
                heapq.heapify(self._heap)
            else:
                heapq.heappush(self._heap, item)
        return True

    async def get(self, poll_interval: float = 0.2) -> dict[str, Any]:
        while True:
            with self._lock:
                while self._heap:
                    item = heapq.heappop(self._heap)
                    if time.time() - item.timestamp <= item.ttl:
                        return item.payload
            await asyncio.sleep(poll_interval)

    def qsize(self) -> int:
        with self._lock:
            return len(self._heap)
