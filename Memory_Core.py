import sqlite3
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class VexaMemory:
    def __init__(self, db_path="database/streamer_brain.db"):
        self.db_path = db_path
        
    def get_recent_context(self, current_message, limit=3):
        """Ищет в базе события, похожие на текущую тему разговора"""
        try:
            if not os.path.exists(self.db_path):
                return ""

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Достаем последние 100 диалогов для анализа смысла
            cursor.execute("SELECT author, message, response FROM events ORDER BY id DESC LIMIT 100")
            rows = cursor.fetchall()
            conn.close()
            
            if not rows or len(rows) < 2:
                return ""

            # Готовим тексты для сравнения (сообщения зрителей)
            history_messages = [r[1] for r in rows]
            
            # Используем векторный поиск (TF-IDF), чтобы найти похожий смысл
            texts = [current_message] + history_messages
            vectorizer = TfidfVectorizer().fit_transform(texts)
            vectors = vectorizer.toarray()
            
            # Считаем косинусное сходство текущего вопроса с историей
            cosine_sim = cosine_similarity(vectors[0:1], vectors[1:])[0]
            
            # Выбираем индексы наиболее похожих записей
            related_indices = cosine_sim.argsort()[-limit:][::-1]
            
            memory_fragments = []
            for i in related_indices:
                if cosine_sim[i] > 0.25: # Порог «узнавания» темы
                    author, msg, resp = rows[i]
                    memory_fragments.append(f"Ранее {author} спрашивал: '{msg}', и ты ответила: '{resp}'")
            
            if memory_fragments:
                return "\n--- ТВОИ ВОСПОМИНАНИЯ ---\n" + "\n".join(memory_fragments)
            return ""
            
        except Exception as e:
            print(f"⚠️ Ошибка поиска в памяти: {e}")
            return ""

# Экземпляр для импорта
vexa_memory = VexaMemory()
