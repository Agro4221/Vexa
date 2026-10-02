# Vexa

> **RU:** Vexa — проект автономной AI-стримерши / AI VTuber, которая должна не просто отвечать на сообщения, а воспринимать события, выбирать, на что обратить внимание, поддерживать контекст и самостоятельно действовать во время стрима.
>
> Изначальная идея Vexa была именно такой: **автономная нейростримерша**, а не Discord-ассистент. По замыслу проект находится в той же концептуальной области, что Овсянка (Grettach), Юна (NEBEYOND), Neuro-Sama (Vedal987) и Neurona (furrydev2007). Discord, Telegram, Twitch, YouTube и остальные платформы здесь — средства взаимодействия Vexa с внешним миром, а не конечная цель проекта.
>
> **EN:** Vexa is a project for an autonomous AI streamer / AI VTuber that is meant to do more than answer messages: it should perceive events, decide what deserves attention, keep context and act on its own during a stream.
>
> The original idea behind Vexa was exactly this: an **autonomous AI streamer**, not a Discord assistant. Conceptually, it belongs to the same space as projects such as Ovsjanka (Grettach), Yuna (NEBEYOND), Neuro-Sama (Vedal987) and Neurona (furrydev2007). Discord, Telegram, Twitch, YouTube and the other platforms are integrations that let Vexa interact with the outside world, not the project's end goal.

> **🚧 Status / Статус:** Advanced prototype / продвинутый прототип. Архитектура автономного стримера уже собрана из отдельных подсистем, но полноценная работа как постоянно действующей нейростримерши всё ещё требует live-проверок, настройки моделей, внешних сервисов и дальнейшей стабилизации.

## 🎭 Core idea / Главная идея

The goal is to build Vexa as an autonomous streamer runtime rather than a conventional chatbot or platform bot.

Главная идея — постепенно собрать систему, которая может:

- получать события из чатов, голоса, экрана и подключённых сервисов;
- решать, какие события важны прямо сейчас;
- использовать память и текущее состояние для формирования контекста;
- обращаться к LLM для генерации реакции;
- превращать реакцию в речь, сообщение или другое действие;
- работать как единый персонаж поверх нескольких платформ.

~~~mermaid
flowchart LR
    WORLD["Stream / Outside world"] --> EVENTS["Events"]
    EVENTS --> ATT["Attention"]
    ATT --> BUS["Event Bus"]
    BUS --> MEM["Memory / Context"]
    MEM --> BRAIN["Core Brain / LLM"]
    BRAIN --> ACT["Actions"]

    ACT --> VOICE["TTS / Voice"]
    ACT --> CHAT["Chat replies"]
    ACT --> VTS["VTube Studio"]
    ACT --> STREAM["Other stream controls"]

    SCREEN["Screen Vision"] --> EVENTS
    MIC["Microphone"] --> EVENTS
    STATE["Vexa State"] <--> BUS
    DB["SQLite"] <--> MEM
    SUP["Supervisor"] --> BUS
    SUP --> VOICE
~~~

## 🧩 What Vexa is / Чем Vexa является

**RU:** Vexa — это не «бот для Discord с AI». Discord является лишь одной из интеграций. Центральная часть проекта — runtime самой Vexa: события, внимание, память, LLM, состояние, голос, действия и контроль над подключёнными модулями.

**EN:** Vexa is not an “AI Discord bot”. Discord is only one integration. The central part of the project is Vexa's own runtime: events, attention, memory, LLM reasoning, state, voice, actions and supervision of connected modules.

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
| Autonomous runtime architecture | ✅ | Core components are separated and orchestrated |
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
| Autonomy | 🟡 | Runtime support exists; autonomous behavior is still being developed |
| AI moderation execution | 🟡 | Gated by application logic |
| Full autonomous streamer runtime | ❌ | Requires assembled host + live integrations + long-running validation |

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
