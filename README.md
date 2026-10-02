# Vexa

> **RU:** Vexa — локальный AI-стример/виртуальный ведущий: LLM, память, голос, зрение и интеграции с Discord, Telegram, Twitch, YouTube, VK Play, OBS, VTube Studio и AxelChat.
>
> **EN:** Vexa is a local AI streamer runtime combining an LLM, memory, voice, vision and adapters for Discord, Telegram, Twitch, YouTube, VK Play, OBS, VTube Studio and AxelChat.

> **🚧 Status / Статус:** Advanced prototype / продвинутый прототип. Основные части уже собраны, но полноценный запуск зависит от конкретного компьютера, моделей, внешних сервисов и live-проверок.

## 🧠 Runtime concept / Идея

Vexa is designed as a runtime system rather than a single chatbot script.

~~~mermaid
flowchart LR
    EV["Events"] --> AT["Attention"]
    AT --> BUS["Event Bus"]
    BUS --> MEM["Memory / Context"]
    MEM --> BRAIN["Core Brain / LLM"]
    BRAIN --> ACT["Actions"]
    ACT --> VOICE["TTS / Voice"]
    ACT --> CHAT["Platform replies"]
    ACT --> VTS["VTube Studio"]

    SCREEN["Screen Vision"] --> MEM
    STATE["Vexa State"] <--> BUS
    DB["SQLite"] <--> MEM
    SUP["Supervisor"] --> BUS
    SUP --> VOICE
~~~

## 🏗️ Component map / Карта компонентов

~~~mermaid
graph TD
    MAIN["main.py"] --> BUS["Event_Bus.py"]
    MAIN --> ATT["Attention_Manager.py"]
    MAIN --> STATE["Vexa_State.py"]
    MAIN --> BRAIN["Core_Brain.py"]
    MAIN --> MEM["Memory_Core.py"]
    MAIN --> SUP["Supervisor.py"]

    BRAIN --> LLM["Ollama / LLM"]
    MEM --> DB["Data_Base.py"]

    MAIN --> DIS["Discord"]
    MAIN --> TG["Telegram"]
    MAIN --> TW["Twitch"]
    MAIN --> YT["YouTube"]
    MAIN --> VK["VK Play"]
    MAIN --> OBS["OBS"]
    MAIN --> VTS["VTube Studio"]

    MAIN --> VISION["Vision"]
    MAIN --> STT["Whisper STT"]
    MAIN --> TTS["Silero TTS"]
    MAIN --> AXEL["AxelChat"]
~~~

## 📊 Current state / Состояние

| Subsystem | State | Notes |
|---|---|---|
| Core orchestration | ✅ | Modular runtime and supervised services |
| Event Bus | ✅ | Bounded priority event handling |
| Attention | ✅ | Scheduling / prioritization |
| Persistent memory | ✅ | SQLite-backed storage |
| LLM layer | ✅ | Configurable provider/model |
| Sensitive-data filtering | ✅ | Dedicated sanitization layer |
| Discord | 🟡 | Integration exists; live auth required |
| Telegram | 🟡 | User-session/news paths exist |
| Twitch | 🟡 | Adapter exists; live auth required |
| YouTube | 🟡 | OAuth/live paths exist |
| VK Play | 🟡 | Configurable adapter |
| OBS | 🟡 | Optional local integration |
| VTube Studio | 🟡 | Optional local integration |
| Screen vision | 🟡 | Model/hardware dependent |
| Whisper STT | 🟡 | Lazy-loaded and configurable |
| Silero TTS | 🟡 | External model required |
| AxelChat | 🟡 | Depends on external messages.ini format |
| Autonomy | 🟡 | Present, disabled by default |
| AI moderation execution | 🟡 | Gated by application logic |
| Full production runtime | ❌ | Requires assembled host + live credentials |

## 🔁 Example event flow / Пример обработки

~~~mermaid
sequenceDiagram
    participant S as Source
    participant E as Event Bus
    participant A as Attention
    participant M as Memory
    participant L as LLM
    participant X as Actions
    participant T as TTS
    participant P as Platform

    S->>E: Message / event
    E->>A: Queue
    A->>M: Context request
    M-->>A: Relevant memory
    A->>L: Message + context
    L-->>X: Response
    X->>T: Clean text
    T-->>P: Voice
    X->>P: Reply / action
    X->>M: Persist event
~~~

## 👁️ Vision + 🎙️ Audio

~~~mermaid
flowchart LR
    MIC["Microphone"] --> STT["Whisper STT"]
    STT --> E["Event Bus"]
    E --> L["LLM"]
    L --> CLEAN["Text cleanup"]
    CLEAN --> TTS["Silero TTS"]
    TTS --> OUT["Voice output"]

    SCREEN["Desktop / window"] --> V["Vision"]
    V --> E
~~~

## 🔌 Integrations / Интеграции

**Discord:** chat, voice and optional voice receive.

**Telegram:** user-session based news processing and publishing.

**Twitch / YouTube / VK Play:** provider-specific adapters behind the common runtime.

**OBS / VTube Studio:** optional local presentation/control integrations.

**AxelChat:** watches external session files and converts incoming chat into runtime events.

## 🔐 Security / Безопасность

Vexa treats platform messages and web content as untrusted input.

The project includes runtime-only credentials, sensitive-data filtering, explicit feature gates and separation between model output and application actions.

The runtime does not blindly execute a model-generated moderation command.

## 🧪 Verification / Проверка

~~~mermaid
flowchart LR
    A["Compile / import"] --> B["Unit tests"]
    B --> C["Secret hygiene"]
    C --> D["Integration checks"]
    D --> E["Live platform auth"]
    E --> F["Soak / long-running"]
~~~

Automated tests cannot replace live authorization and host-specific testing.

## ⚙️ Configuration / Конфигурация

Create .env from .env.example.

The configuration covers LLM, STT/TTS, vision, Discord, Telegram, Twitch, YouTube, VK Play, OBS, VTube Studio, AxelChat, autonomy and moderation policies.

## 🗺️ Roadmap / План развития

~~~mermaid
flowchart LR
    A["Advanced prototype"] --> B["More stable runtime"]
    B --> C["Live integrations"]
    C --> D["Recovery / reliability"]
    D --> E["Long-running tests"]
    E --> F["Stable release"]
~~~

## 🧑‍💻 About the author / Об авторе

**RU:** Я пока новичок и учусь разработке прямо на Vexa. Это один из моих самых больших практических проектов: здесь я постепенно разбираюсь с Python, асинхронностью, API, LLM, базами данных, голосом, компьютерным зрением и архитектурой сложных приложений. Поэтому некоторые решения экспериментальные — и это нормально для текущего этапа проекта.

**EN:** I am still a beginner developer and I am learning by building Vexa. It is one of my largest practical projects, combining Python, async programming, APIs, LLMs, databases, voice, computer vision and larger application architecture. Some parts are experimental, which is expected at this stage.

## 📁 Important files / Основные файлы

~~~text
main.py                  # runtime orchestrator
Event_Bus.py             # event queue
Attention_Manager.py     # attention scheduling
Vexa_State.py            # runtime state
Core_Brain.py            # LLM layer
Memory_Core.py           # contextual memory
Data_Base.py             # persistence
Supervisor.py            # service supervision
Health_Check.py          # diagnostics

Discord_Module.py        # Discord integration
TG_Module.py             # Telegram integration
Twitch_Module.py         # Twitch integration
YouTube_Module.py        # YouTube integration
VK_Module.py             # VK Play integration
OBS_Module.py            # OBS integration
VTS_Module.py            # VTube Studio
Vision_Module.py         # screen vision
TTS_Manager.py           # text-to-speech
AxelChat_Watcher.py      # external chat watcher
Sensitive_Data_Filter.py # secret filtering
~~~

---

**RU:** Vexa развивается вместе с моими навыками.

**EN:** Vexa grows together with my skills.
