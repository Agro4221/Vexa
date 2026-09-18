from __future__ import annotations

import asyncio
import heapq
import itertools
from dataclasses import dataclass, field
from typing import Awaitable, Callable


@dataclass(order=True)
class _Speech:
    priority: int
    sequence: int
    text: str = field(compare=False)
    guild_id: int | None = field(compare=False)


class TTSManager:
    def __init__(self, max_size: int | None = None) -> None:
        import config
        self.max_size = max(1, max_size or config.TTS_QUEUE_MAX_SIZE)
        self._heap: list[_Speech] = []
        self._sequence = itertools.count()
        self._condition = asyncio.Condition()
        self._speaker: Callable[[str, int | None], Awaitable[object]] | None = None
        self._task: asyncio.Task | None = None
        self._stopping = False

    def bind(
        self,
        speaker: Callable[[str, int | None], Awaitable[object]],
    ) -> None:
        self._speaker = speaker
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.create_task(
                self._run(),
                name="vexa:tts",
            )

    def enqueue(
        self,
        text: str,
        guild_id: int | None,
        priority: int = 3,
    ) -> bool:
        if not text or self._speaker is None:
            return False

        item = _Speech(
            priority=max(0, min(3, int(priority))),
            sequence=next(self._sequence),
            text=text,
            guild_id=guild_id,
        )
        if len(self._heap) >= self.max_size:
            worst_index = max(
                range(len(self._heap)),
                key=lambda i: (
                    self._heap[i].priority,
                    self._heap[i].sequence,
                ),
            )
            worst = self._heap[worst_index]
            if item.priority >= worst.priority:
                return False
            self._heap[worst_index] = item
            heapq.heapify(self._heap)
        else:
            heapq.heappush(self._heap, item)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._notify())
        except RuntimeError:
            pass
        return True

    async def _notify(self) -> None:
        async with self._condition:
            self._condition.notify(1)

    async def _get(self) -> _Speech | None:
        while not self._stopping:
            async with self._condition:
                if self._heap:
                    return heapq.heappop(self._heap)
                await self._condition.wait()
        return None

    async def _run(self) -> None:
        while not self._stopping:
            try:
                item = await self._get()
                if item is None or self._speaker is None:
                    continue
                try:
                    import config

                    await asyncio.wait_for(
                        self._speaker(
                            item.text,
                            item.guild_id,
                        ),
                        timeout=config.TTS_TIMEOUT,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    from logger import log_event

                    log_event(
                        "TTS_ERR",
                        "Отдельный TTS worker пережил ошибку озвучки.",
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                from logger import log_event

                log_event(
                    "TTS_ERR",
                    "TTS worker пережил внутреннюю ошибку.",
                )
                await asyncio.sleep(0.5)

    def clear_pending(self) -> None:
        self._heap.clear()

    async def stop(self) -> None:
        self._stopping = True
        self.clear_pending()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(
                self._task,
                return_exceptions=True,
            )
        self._task = None


tts_manager = TTSManager()