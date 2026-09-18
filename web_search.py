from __future__ import annotations
from logger import log_event

def search_internet(query:str,max_results:int=5)->str:
    if not query.strip(): return ""
    try:
        from ddgs import DDGS
    except ImportError:
        log_event("SEARCH","Пакет ddgs не установлен; поиск отключён."); return ""
    try:
        with DDGS() as ddgs:
            results=list(ddgs.text(query,max_results=max_results))
        return "\n".join(f"- {r.get('title','')}\n  {r.get('body','')}\n  URL: {r.get('href','')}" for r in results)
    except Exception as exc:
        log_event("SEARCH_ERR",f"Ошибка поиска: {exc}"); return ""
