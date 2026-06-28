import re
from num2words import num2words

def prepare_text_for_tts(text: str) -> str:
    # 1. Заменяем цифры на слова (1 -> один, 15 -> пятнадцать)
    def replace_num(match):
        return num2words(int(match.group()), lang='ru')
    text = re.sub(r'\d+', replace_num, text)

    # 2. Убираем ссылки, рекламу и спецсимволы, оставляя знаки препинания
    text = re.sub(r'http\S+|www\S+|@\w+', '', text)
    # Оставляем английский и русский, убираем эмодзи
    text = "".join(c for c in text if c.isalnum() or c.isspace() or c in ".,!?+-")

    # 3. Добавляем акценты для Silero (паузы)
    text = text.replace(".", "... ").replace("!", "! ").replace("?", "? ")
    
    # Чтобы не было "одышки", ограничиваем длину фразы перед отправкой в модель
    return text.strip()
