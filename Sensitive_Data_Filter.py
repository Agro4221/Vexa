from __future__ import annotations

import re
from typing import Any

_PATTERNS = (
    re.compile(r"(?i)(oauth:)[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)(bot)\d{7,12}:[A-Za-z0-9_-]{20,}"),
    re.compile(r"(?i)(gocspx-)[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._-]{20,}"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)[^\s,;]+"),
    re.compile(r"(?i)(token\s*[=:]\s*)[^\s,;]+"),
)


def sanitize_text(text: str) -> str:
    value = str(text)
    for pattern in _PATTERNS:
        value = pattern.sub(r"\1[REDACTED]", value)
    return value


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_value(item) for item in value)
    if isinstance(value, dict):
        return {
            key: sanitize_value(item)
            for key, item in value.items()
        }
    return value
