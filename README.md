# 🎭 Vexa — Autonomous AI Streamer / AI VTuber

> **Vexa** — попытка собрать автономную AI-стримершу, которая воспринимает события стрима, выбирает, на что обратить внимание, использует память и LLM, говорит голосом и взаимодействует с внешним миром.
>
> Это **не Discord-бот**, вокруг которого случайно добавили AI. Изначальная идея Vexa — именно автономная нейростримерша в духе проектов **Овсянка (Grettach), Юна (NEBEYOND), Neuro-Sama (Vedal987) и Neurona (furrydev2007)**. Discord, Telegram, Twitch, YouTube, VK Play, OBS и VTube Studio — это подключаемые интерфейсы и инструменты, через которые Vexa получает события и действует.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/LLM-Ollama-111111)
![Twitch](https://img.shields.io/badge/Twitch-integration-9146FF?logo=twitch&logoColor=white)
![YouTube](https://img.shields.io/badge/YouTube-integration-FF0000?logo=youtube&logoColor=white)
![Discord](https://img.shields.io/badge/Discord-integration-5865F2?logo=discord&logoColor=white)
![VTube Studio](https://img.shields.io/badge/VTube%20Studio-API-FF69B4)

> 🚧 **Статус:** **Advanced Prototype / Продвинутый прототип**
>
> Основная архитектура уже собрана и разделена на подсистемы, но Vexa пока не является законченной постоянно работающей автономной нейростримершей. Для этого ещё нужны live-проверки платформ, стабильность долгих запусков, доработка автономного поведения и настройка конкретного хоста.

## ✨ Что уже умеет Vexa

| Возможность | Статус |
|---|---|
| 🧠 Центральный runtime и оркестрация | ✅ |
| 🔄 Event Bus для событий от разных источников | ✅ |
| 🎯 Attention Manager — приоритизация событий | ✅ |
| 💾 Контекстная память на SQLite | ✅ |
| 🤖 Настраиваемый LLM через Ollama | ✅ |
| 🔐 Фильтрация чувствительных данных | ✅ |
| 🎙️ Локальный TTS через Silero | ✅, модель нужна |
| 🎤 Speech-to-Text через faster-whisper | ✅, опционально |
| 👁️ Компьютерное зрение экрана | 🟡, зависит от модели/железа |
| 🎭 Управление VTube Studio | 🟡 |
| 🟣 Twitch | 🟡, нужна live-проверка |
| 🔵 YouTube | 🟡, нужен OAuth/live-тест |
| 💬 Discord + voice | 🟡 |
| 📣 Telegram | 🟡 |
| 🔷 VK Play | 🟡 |
| 🎛️ OBS | 🟡 |
| 💬 AxelChat | 🟡 |
| 🧬 Автономное поведение | 🟡, активно развивается |
| 🛡️ AI-модерация | 🟡, намеренно ограничена защитными проверками |
| ♾️ Надёжная работа 24/7 | ❌, пока не заявляется |

## 🧠 Какой должна быть Vexa

Идея проекта — не просто «получить сообщение → отправить ответ».

Vexa постепенно строится вокруг цикла:

```text
  CHAT / VOICE / SCREEN / STREAM EVENTS
                    │
                    ▼
             ┌─────────────┐
             │ Attention   │
             │ Manager     │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │  Event Bus  │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │   Memory    │
             │ + Context   │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │ Core Brain  │
             │    + LLM    │
             └──────┬──────┘
                    ▼
             ┌─────────────┐
             │   Actions   │
             └───┬─────┬───┘
                 │     │
          ┌──────┘     └─────────┐
          ▼                      ▼
     TTS / Voice          Chat / Stream / VTS
```

Именно этот runtime является центром проекта. Платформенные модули подключаются вокруг него.

## 🏗️ Архитектура

~~~mermaid
flowchart LR
    WORLD["Twitch / YouTube / Discord / Telegram / VK Play"] --> EVENTS["Incoming events"]
    MIC["Microphone"] --> EVENTS
    SCREEN["Screen vision"] --> EVENTS

    EVENTS --> ATT["Attention Manager"]
    ATT --> BUS["Event Bus"]
    BUS <--> STATE["Vexa State"]
    BUS --> MEM["Memory / Context"]
    MEM <--> DB["SQLite"]

    MEM --> BRAIN["Core Brain"]
    BRAIN --> LLM["Ollama / LLM"]

    BRAIN --> ACTIONS["Action Manager"]
    ACTIONS --> TTS["Silero TTS"]
    ACTIONS --> CHAT["Platform replies"]
    ACTIONS --> VTS["VTube Studio"]
    ACTIONS --> OBS["OBS / stream control"]

    SUP["Supervisor"] --> BUS
    SUP --> TTS
    SUP --> ACTIONS
~~~

## 🧩 Компоненты

~~~mermaid
graph TD
    MAIN["main.py"] --> BUS["Event_Bus.py"]
    MAIN --> ATT["Attention_Manager.py"]
    MAIN --> STATE["Vexa_State.py"]
    MAIN --> BRAIN["Core_Brain.py"]
    MAIN --> MEM["Memory_Core.py"]
    MAIN --> ACTION["Action_Manager.py"]
    MAIN --> SUP["Supervisor.py"]
    MAIN --> AUTO["Autonomy_Manager.py"]

    BRAIN --> LLM["Ollama"]
    MEM --> DB["Data_Base.py"]

    MAIN --> TW["Twitch"]
    MAIN --> YT["YouTube"]
    MAIN --> DIS["Discord"]
    MAIN --> TG["Telegram"]
    MAIN --> VK["VK Play"]

    MAIN --> OBS["OBS"]
    MAIN --> VTS["VTube Studio"]
    MAIN --> VISION["Vision"]
    MAIN --> STT["Whisper"]
    MAIN --> TTS["Silero"]
    MAIN --> AXEL["AxelChat"]
~~~

## 🔁 Пример обработки события

~~~mermaid
sequenceDiagram
    participant S as Источник
    participant B as Event Bus
    participant A as Attention
    participant M as Memory
    participant L as LLM
    participant X as Actions
    participant T as TTS
    participant P as Platform

    S->>B: Сообщение / событие
    B->>A: Приоритизация
    A->>M: Запрос контекста
    M-->>A: Релевантная память
    A->>L: Событие + контекст
    L-->>X: Ответ / intent
    X->>T: Подготовленный текст
    T-->>P: Голос
    X->>P: Сообщение / действие
    X->>M: Сохранение события
~~~

## 👁️ Зрение и 🎙️ голос

~~~mermaid
flowchart LR
    MIC["Микрофон"] --> STT["faster-whisper"]
    STT --> BUS["Event Bus"]
    BUS --> BRAIN["Core Brain / LLM"]
    BRAIN --> CLEAN["Text cleanup"]
    CLEAN --> TTS["Silero TTS"]
    TTS --> VOICE["Voice output"]

    SCREEN["Экран / окно"] --> VISION["Vision model"]
    VISION --> BUS
~~~

Эта часть нужна для будущей модели взаимодействия, в которой Vexa реагирует не только на текст чата, но и на собственную речь, голосовой ввод и визуальный контекст.

## 🔌 Интеграции

**Twitch** — основная stream-facing интеграция, к которой в перспективе должен подключаться автономный цикл стримера.

**YouTube** — live chat/OAuth-контур.

**Discord** — текстовый и голосовой канал, а не основная цель проекта.

**Telegram** — события, взаимодействие и новостные сценарии.

**VK Play** — отдельный адаптер платформы.

**OBS / VTube Studio** — управление презентацией и аватаром.

**AxelChat** — дополнительный источник внешнего чата.

Все интеграции должны оставаться заменяемыми модулями вокруг ядра Vexa.

## 🛡️ Безопасность

Внешние сообщения, веб-контент и данные платформ считаются **недоверенным вводом**.

В проекте предусмотрены:

- фильтрация чувствительных данных;
- runtime-only секреты;
- явные feature gates;
- разделение LLM-ответа и выполнения действий;
- защитные проверки для потенциально опасных функций.

Vexa не должна слепо выполнять команду только потому, что её сгенерировала модель.

Для автономного стримера это особенно важно: **«модель решила» и «программа разрешила действие» — разные этапы.**

## ⚙️ Настройка

Основная конфигурация находится в `.env`.

Создай локальный файл:

```text
.env
```

на основе:

```text
.env.example
```

Основные группы настроек:

```text
LLM / Ollama
TTS / STT
Vision
Twitch
YouTube
Discord
Telegram
VK Play
OBS
VTube Studio
AxelChat
Autonomy
Moderation
```

Реальные ключи, токены и локальные runtime-данные не должны попадать в Git.

## 🚀 Быстрый старт

### 1. Установить зависимости

```powershell
python -m pip install -r requirements.txt
```

### 2. Подготовить Ollama

Установи локальный Ollama и скачай совместимую модель.

Параметры выбора модели находятся в `.env`:

```text
VEXA_LLM_PROVIDER=ollama
VEXA_MODEL=
OLLAMA_AUTO_SELECT_MODEL=true
```

### 3. Настроить окружение

Скопируй:

```text
.env.example → .env
```

и включи только те интеграции, которые действительно нужны.

### 4. Запустить диагностику

```powershell
python Health_Check.py
```

### 5. Запустить Vexa

```powershell
python main.py
```

Для первого запуска лучше начать с локального LLM + TTS и подключать платформы по одной.

## 🧪 Проверка

~~~mermaid
flowchart LR
    A["Compile / import"] --> B["Unit tests"]
    B --> C["Secret hygiene"]
    C --> D["Integration checks"]
    D --> E["Live auth"]
    E --> F["Long-running / soak test"]
~~~

Автоматические проверки не заменяют реальный запуск на конкретном ПК: модели, GPU/CPU, аудио, драйверы и авторизация внешних платформ всё равно требуют проверки на хосте.

## 🗺️ Roadmap

~~~mermaid
flowchart LR
    A["Advanced prototype"] --> B["Stable event runtime"]
    B --> C["Reliable attention + memory"]
    C --> D["Live Twitch streamer loop"]
    D --> E["Better autonomy"]
    E --> F["Recovery / long-running"]
    F --> G["Stable AI VTuber runtime"]
~~~

Главное направление — не наращивать количество функций Discord-бота, а довести Vexa до состояния, в котором она сможет **стабильно жить как автономная AI-стримерша**, сохраняя контекст и взаимодействуя с аудиторией.

## 🧑‍💻 Об авторе

Я пока **новичок в разработке** и учусь прямо в процессе создания Vexa. Проект для меня одновременно является большой практической разработкой и учебной лабораторией: здесь я разбираюсь с Python, асинхронностью, API, LLM, базами данных, аудио, компьютерным зрением и архитектурой большого приложения.

Поэтому часть решений пока экспериментальная. README намеренно не маскирует этот факт под «production-ready».

## 📁 Основные файлы

~~~text
main.py                   # основной runtime
config.py                 # конфигурация
Event_Bus.py              # шина событий
Attention_Manager.py      # внимание / приоритизация
Autonomy_Manager.py       # автономное поведение
Vexa_State.py             # состояние Vexa
Core_Brain.py             # LLM-слой
Memory_Core.py            # контекстная память
Data_Base.py              # хранение данных
Action_Manager.py         # выполнение разрешённых действий
Supervisor.py             # контроль сервисов
Health_Check.py           # диагностика

Discord_Module.py         # Discord
TG_Module.py              # Telegram
Twitch_Module.py          # Twitch
YouTube_Module.py         # YouTube
VK_Module.py              # VK Play
OBS_Module.py             # OBS
VTS_Module.py             # VTube Studio
Vision_Module.py          # экран / vision
TTS_Manager.py            # синтез речи
AxelChat_Watcher.py       # внешний чат
Sensitive_Data_Filter.py  # фильтрация чувствительных данных
~~~

---

> 🎭 **Vexa развивается вместе с моими навыками.**
>
> Это не готовый коммерческий продукт и не попытка притвориться им. Это живой проект по созданию собственной автономной AI-стримерши — от архитектуры и первых модулей до будущего полноценного стримового runtime.
