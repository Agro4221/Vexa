from __future__ import annotations

import re

_URL_RE = re.compile(r"(https?://\S+|www\.\S+|@\w+)")
_NUM_RE = re.compile(r"\d+")


def prepare_text_for_tts(text: str, max_chars: int = 700) -> str:
    if not text:
        return ""

    def replace_num(match):
        try:
            from num2words import num2words

            return num2words(int(match.group()), lang="ru")
        except (ImportError, ValueError, OverflowError):
            return match.group()

    text = _URL_RE.sub("", text)
    text = _NUM_RE.sub(replace_num, text)
    text = "".join(
        c for c in text if c.isalnum() or c.isspace() or c in ".,!?;:()'-+%/"
    )
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].strip() + "…"
    return text
