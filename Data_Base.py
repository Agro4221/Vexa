from __future__ import annotations
import datetime as dt
import sqlite3
from pathlib import Path
import config

class GlobalMemory:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path=Path(db_path or config.DB_PATH)
        self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.setup_db()

    def _connect(self)->sqlite3.Connection:
        conn=sqlite3.connect(self.db_path,timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        return conn

    def setup_db(self)->None:
        with self._connect() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                platform TEXT NOT NULL,
                author TEXT NOT NULL,
                message TEXT NOT NULL,
                ai_response TEXT NOT NULL DEFAULT '',
                mood INTEGER NOT NULL DEFAULT 50,
                screenshot_path TEXT NOT NULL DEFAULT ''
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS tg_posts (
                post_hash TEXT PRIMARY KEY,
                channel_id TEXT NOT NULL DEFAULT '',
                message_id TEXT NOT NULL DEFAULT '',
                date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'published'
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS viewer_profiles (
                platform TEXT NOT NULL,
                user_id TEXT NOT NULL,
                display_name TEXT NOT NULL,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                interaction_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(platform,user_id)
            )""")

    def is_duplicate(self,post_hash:str)->bool:
        with self._connect() as conn:
            return conn.execute("SELECT 1 FROM tg_posts WHERE post_hash=? AND status='published'",(post_hash,)).fetchone() is not None

    def claim_tg_post(self,post_hash:str,channel_id:str="",message_id:str="")->bool:
        now=dt.datetime.now().isoformat()
        with self._connect() as conn:
            cur=conn.execute("INSERT OR IGNORE INTO tg_posts(post_hash,channel_id,message_id,date,status) VALUES(?,?,?,?, 'processing')",
                             (post_hash,str(channel_id),str(message_id),now))
            return cur.rowcount==1

    def mark_tg_published(self,post_hash:str,message_id:str="")->None:
        with self._connect() as conn:
            conn.execute("UPDATE tg_posts SET message_id=?,status='published',date=? WHERE post_hash=?",
                         (str(message_id),dt.datetime.now().isoformat(),post_hash))

    def release_tg_claim(self,post_hash:str)->None:
        with self._connect() as conn:
            conn.execute("DELETE FROM tg_posts WHERE post_hash=? AND status='processing'",(post_hash,))

    def add_tg_post(self,post_hash:str)->None:
        if self.claim_tg_post(post_hash): self.mark_tg_published(post_hash)

    def add_event(self,platform:str,author:str,message:str,response:str="",mood:int=50,screenshot:str="")->None:
        now=dt.datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute("INSERT INTO events(timestamp,platform,author,message,ai_response,mood,screenshot_path) VALUES(?,?,?,?,?,?,?)",
                         (now,platform,author,message,response,int(mood),screenshot))
            conn.execute("""INSERT INTO viewer_profiles(platform,user_id,display_name,first_seen,last_seen,interaction_count)
                            VALUES(?,?,?,?,?,1)
                            ON CONFLICT(platform,user_id) DO UPDATE SET
                            display_name=excluded.display_name,last_seen=excluded.last_seen,
                            interaction_count=interaction_count+1""",
                         (platform,author,author,now,now))

memory=GlobalMemory()
