from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from logger import log_event


class Supervisor:
    """Keeps optional services alive without hot-looping on quick exits."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()
        self._stopping = False

    def start(
        self,
        name: str,
        factory: Callable[[], Awaitable[None]],
        *,
        restart: bool = True,
    ) -> asyncio.Task:
        task = asyncio.create_task(
            self._runner(name, factory, restart=restart),
            name=f"vexa:{name}",
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    async def _runner(
        self,
        name: str,
        factory: Callable[[], Awaitable[None]],
        *,
        restart: bool,
    ) -> None:
        delay = 1.0
        while not self._stopping:
            try:
                await factory()
                if not restart or self._stopping:
                    return
                log_event(
                    "SUPERVISOR",
                    f"Сервис {name} завершился; перезапуск через {delay:.0f}с",
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 60.0)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log_event(
                    "SUPERVISOR",
                    f"Сервис {name} упал: {exc}; перезапуск через {delay:.0f}с",
                )
                if not restart:
                    return
                await asyncio.sleep(delay)
                delay = min(delay * 2.0, 60.0)

    async def stop(self) -> None:
        self._stopping = True
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
