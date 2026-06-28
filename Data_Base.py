import sqlite3
import datetime

class GlobalMemory:
    def __init__(self, db_path="database/streamer_brain.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        # Таблица логов всех событий
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            platform TEXT,
            author TEXT,
            message TEXT,
            ai_response TEXT,
            mood TEXT,
            screenshot_path TEXT
        )''')
        
        # Таблица для защиты от дубликатов постов ТГ
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS tg_posts (
            post_hash TEXT PRIMARY KEY,
            date TEXT
        )''')
        self.conn.commit()

    def is_duplicate(self, post_hash):
        self.cursor.execute("SELECT 1 FROM tg_posts WHERE post_hash = ?", (post_hash,))
        return self.cursor.fetchone() is not None

    def add_tg_post(self, post_hash):
        self.cursor.execute("INSERT OR IGNORE INTO tg_posts (post_hash, date) VALUES (?, ?)", 
                            (post_hash, datetime.datetime.now().isoformat()))
        self.conn.commit()

    def add_event(self, platform, author, message, response="", mood="neutral", screenshot=""):
        self.cursor.execute(
            "INSERT INTO events (timestamp, platform, author, message, ai_response, mood, screenshot_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (datetime.datetime.now().isoformat(), platform, author, message, response, mood, screenshot)
        )
        self.conn.commit()

# Инициализация памяти
memory = GlobalMemory()
