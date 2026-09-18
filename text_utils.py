from __future__ import annotations
import re
from num2words import num2words

_URL_RE=re.compile(r"(https?://\S+|www\.\S+|@\w+)")
_NUM_RE=re.compile(r"\d+")

def prepare_text_for_tts(text:str,max_chars:int=700)->str:
    if not text:
        return ""
    def repl(m):
        try:
            return num2words(int(m.group(0)),lang="ru")
        except (ValueError,OverflowError):
            return m.group(0)
    text=_URL_RE.sub("",text)
    text=_NUM_RE.sub(repl,text)
    text="".join(c for c in text if c.isalnum() or c.isspace() or c in ".,!?;:()'-+%/")
    text=re.sub(r"\s+"," ",text).strip()
    if len(text)>max_chars:
        text=text[:max_chars].rsplit(" ",1)[0].strip()+"…"
    return text
