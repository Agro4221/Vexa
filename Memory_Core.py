from __future__ import annotations

import sqlite3
from typing import Optional

from Data_Base import memory
from logger import log_event


class VexaMemory:
    def __init__(self, db=None) -> None:
        self.db = db or memory

    def get_recent_context(
        self,
        current_message: str,
        limit: int = 3,
        platform: Optional[str] = None,
        user_id: str = "",
    ) -> str:
        if not current_message or len(current_message.strip()) < 2:
            return ""
        try:
            with self.db._connect() as conn:
                filters = []
                params: list[str] = []
                if platform:
                    filters.append("platform=?")
                    params.append(platform)
                if user_id:
                    filters.append("user_id=?")
                    params.append(user_id)

                where = f" WHERE {' AND '.join(filters)}" if filters else ""
                rows = conn.execute(
                    "SELECT author,user_id,platform,session_id,source_time,message,ai_response "
                    f"FROM events{where} ORDER BY id DESC LIMIT 300",
                    params,
                ).fetchall()
            if not rows:
                return ""

            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity

                matrix = TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=5000,
                ).fit_transform(
                    [current_message] + [row[5] for row in rows]
                )
                scores = cosine_similarity(matrix[0:1], matrix[1:])[0]
                indices = scores.argsort()[-limit:][::-1]
            except Exception as exc:
                log_event(
                    "MEMORY",
                    f"TF-IDF недоступен, беру последние записи: {exc}",
                )
                indices = range(min(limit, len(rows)))
                scores = [1.0] * len(rows)

            fragments = []
            for i in indices:
                score = float(scores[i]) if i < len(scores) else 1.0
                if score < 0.18:
                    continue
                author, stored_user_id, event_platform, session_id, source_time, msg, response = rows[i]
                origin = event_platform
                if session_id:
                    origin += f", сессия {session_id}"
                if source_time:
                    origin += f", {source_time}"
                fragments.append(
                    f"Ранее {author} ({origin}) говорил: «{msg}». "
                    f"Ты ответила: «{response}»."
                )
            return (
                "
--- ВОСПОМИНАНИЯ ---
" + "
".join(fragments)
                if fragments
                else ""
            )
        except sqlite3.Error as exc:
            log_event("MEMORY_ERR", f"Ошибка памяти: {exc}")
            return ""

    def get_user_history(
        self,
        user_id: str,
        limit: int = 20,
        platform: Optional[str] = None,
    ) -> list[dict[str, str]]:
        if not user_id:
            return []
        try:
            with self.db._connect() as conn:
                if platform:
                    rows = conn.execute(
                        "SELECT platform,author,user_id,session_id,source_time,message,ai_response "
                        "FROM events WHERE user_id=? AND platform=? ORDER BY id DESC LIMIT ?",
                        (user_id, platform, limit),
                    ).fetchall()
                else:
                    rows = conn.execute(
                        "SELECT platform,author,user_id,session_id,source_time,message,ai_response "
                        "FROM events WHERE user_id=? ORDER BY id DESC LIMIT ?",
                        (user_id, limit),
                    ).fetchall()
            return [
                {
                    "platform": row[0],
                    "author": row[1],
                    "user_id": row[2],
                    "session_id": row[3],
                    "source_time": row[4],
                    "message": row[5],
                    "response": row[6],
                }
                for row in rows
            ]
        except sqlite3.Error as exc:
            log_event("MEMORY_ERR", f"Ошибка истории пользователя: {exc}")
            return []


vexa_memory = VexaMemory()
