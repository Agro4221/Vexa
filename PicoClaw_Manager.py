
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any, Callable

import config
from logger import log_event


class ToolRegistry:
    """Explicitly enabled tools inspired by PicoClaw's per-tool controls."""

    def __init__(self) -> None:
        self._tools: dict[str, Callable[..., Any]] = {}
        self._enabled: set[str] = set()

    def register(
        self,
        name: str,
        func: Callable[..., Any],
        enabled: bool = True,
    ) -> None:
        self._tools[name] = func
        if enabled:
            self._enabled.add(name)

    def enable(self, name: str) -> None:
        if name in self._tools:
            self._enabled.add(name)

    def disable(self, name: str) -> None:
        self._enabled.discard(name)

    def list_tools(self) -> list[str]:
        return sorted(self._enabled)

    def call(self, name: str, *args, **kwargs) -> Any:
        if name not in self._enabled:
            raise PermissionError(f"Tool disabled: {name}")
        return self._tools[name](*args, **kwargs)


class SkillRegistry:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(
            root or (config.DATA_DIR / "skills")
        )
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def discover(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for path in self.root.glob("*/SKILL.md"):
            try:
                result[path.parent.name] = path.read_text(
                    encoding="utf-8"
                )
            except OSError as exc:
                log_event(
                    "SKILLS_ERR",
                    f"Не удалось прочитать {path}: {exc}",
                )
        return result

    def ensure_default(self) -> None:
        path = self.root / "vexa-runtime" / "SKILL.md"
        if path.exists():
            return
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        path.write_text(
            """---
name: vexa-runtime
description: Базовые правила runtime Vexa.
---
Сохраняй модульность, не публикуй секреты, учитывай аварийные стопы
и не выполняй операции за пределами настроенной конфигурации.
""",
            encoding="utf-8",
        )


class Workspace:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(
            root or (config.DATA_DIR / "workspace")
        ).resolve()
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _safe(self, relative: str | Path) -> Path:
        target = (
            self.root / Path(relative)
        ).resolve()
        if target != self.root and self.root not in target.parents:
            raise PermissionError(
                "Workspace path escape blocked"
            )
        return target

    def read_text(self, relative: str) -> str:
        return self._safe(relative).read_text(
            encoding="utf-8"
        )

    def write_text(
        self,
        relative: str,
        text: str,
    ) -> None:
        target = self._safe(relative)
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        target.write_text(
            text,
            encoding="utf-8",
        )


class SafeExecutor:
    """Optional workspace-only command execution, disabled by default."""

    _DENY = (
        "rm -rf",
        "del /f",
        "rmdir /s",
        "format ",
        "mkfs",
        "diskpart",
        "shutdown",
        "reboot",
        "poweroff",
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    async def run(
        self,
        command: list[str],
        timeout: float = 30.0,
    ) -> tuple[int, str, str]:
        if not config.PICOCLAW_EXEC_ENABLED:
            raise PermissionError(
                "Tool execution is disabled"
            )
        if not command:
            raise ValueError("Empty command")
        joined = " ".join(command).lower()
        if any(item in joined for item in self._DENY):
            raise PermissionError(
                "Command blocked by execution policy"
            )

        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(self.workspace.root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise

        return (
            process.returncode,
            stdout.decode("utf-8", errors="replace"),
            stderr.decode("utf-8", errors="replace"),
        )


skills = SkillRegistry()
workspace = Workspace()
tools = ToolRegistry()
executor = SafeExecutor(workspace)
