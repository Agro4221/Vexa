from __future__ import annotations
import sqlite3
from typing import Optional
from Data_Base import memory
from logger import log_event

class VexaMemory:
    def __init__(self,db=None)->None:
        self.db=db or memory

    def get_recent_context(self,current_message:str,limit:int=3,platform:Optional[str]=None)->str:
        if not current_message or len(current_message.strip())<2: return ""
        try:
            with self.db._connect() as conn:
                if platform:
                    rows=conn.execute("SELECT author,message,ai_response FROM events WHERE platform=? ORDER BY id DESC LIMIT 200",(platform,)).fetchall()
                else:
                    rows=conn.execute("SELECT author,message,ai_response FROM events ORDER BY id DESC LIMIT 200").fetchall()
            if not rows: return ""
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                matrix=TfidfVectorizer(ngram_range=(1,2),min_df=1).fit_transform([current_message]+[r[1] for r in rows])
                scores=cosine_similarity(matrix[0:1],matrix[1:])[0]
                indices=scores.argsort()[-limit:][::-1]
            except Exception as exc:
                log_event("MEMORY",f"TF-IDF недоступен, беру последние записи: {exc}")
                indices=range(min(limit,len(rows))); scores=[1.0]*len(rows)
            fragments=[]
            for i in indices:
                score=float(scores[i]) if i < len(scores) else 1.0
                if score<0.18: continue
                author,msg,response=rows[i]
                fragments.append(f"Ранее {author} говорил: «{msg}». Ты ответила: «{response}».")
            return "\n--- ВОСПОМИНАНИЯ ---\n"+"\n".join(fragments) if fragments else ""
        except sqlite3.Error as exc:
            log_event("MEMORY_ERR",f"Ошибка памяти: {exc}"); return ""

vexa_memory=VexaMemory()
