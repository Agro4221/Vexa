# Vexa

Vexa is a local AI streamer runtime that connects an LLM with voice I/O, optional screen vision, VTube Studio, Discord, Telegram, AxelChat, Twitch, YouTube, VK Play and OBS adapters.

> Current state: advanced prototype / pre-release. Core orchestration, persistence, platform adapters, security filtering and CI are present, but live authorization and host-specific integration testing are still required.

## Architecture

The runtime is split into focused services:

- main.py — orchestration
- Event_Bus.py — bounded priority event queue
- Attention_Manager.py — attention scheduling
- Vexa_State.py — mutable runtime state
- Core_Brain.py — LLM access and response handling
- Memory_Core.py / Data_Base.py — persistent memory
- Supervisor.py / Health_Check.py — service supervision and health
- platform modules — Discord, Telegram, Twitch, YouTube, VK Play, OBS, VTube Studio
- Vision_Module.py / ears.py / TTS_Manager.py — optional perception and speech pipeline

## What works

| Area | State | Notes |
|---|---|---|
| Core orchestration | ✅ | Modular startup and supervised background services |
| Persistent memory | ✅ | SQLite runtime store and context retrieval |
| LLM layer | ✅ | Model/provider selected through environment configuration |
| Text cleanup / response handling | ✅ | Includes sensitive-data filtering |
| Discord integration | 🟡 | Code and voice/chat paths are present; live credentials required |
| Telegram integration | 🟡 | User-session and news paths are present; live authorization required |
| Twitch integration | 🟡 | Chat/metadata adapter is implemented; live auth required |
| YouTube integration | 🟡 | OAuth/live-chat/broadcast paths are implemented; live auth required |
| VK Play | 🟡 | Configurable adapter; undocumented endpoints are not guessed |
| OBS | 🟡 | Optional adapter; requires a real OBS instance |
| VTube Studio | 🟡 | Optional adapter; requires a real VTS instance |
| Screen vision | 🟡 | Lazy-loaded and configurable; hardware/model dependent |
| Whisper STT | 🟡 | Lazy-loaded and configurable |
| Silero TTS | 🟡 | Lazy-loaded; model binary kept outside Git |
| AxelChat watcher | 🟡 | Depends on the external messages.ini format |
| Autonomy | 🟡 | Feature exists but is disabled by default |
| AI moderation execution | ❌ | Intentionally not executed directly from model output |
| Full end-to-end production run | ❌ | Requires a real streaming machine and credentials |

## Setup

Create .env from .env.example.

Install dependencies:

~~~bash
python -m pip install -r requirements.txt
~~~

Optional local audio:

~~~bash
python -m pip install -r requirements-local-audio.txt
~~~

Run validation:

~~~bash
python Health_Check.py
python -m compileall -q .
python -m pytest -q
~~~

Then start the runtime:

~~~bash
python main.py
~~~

## Configuration

Credentials and deployment-specific values are environment variables. The public repository contains no real service tokens, OAuth secrets, Telegram channel IDs, runtime databases or user-specific filesystem paths.

Important variables include:

- Discord credentials
- Telegram API/session settings
- Twitch/YouTube/VK credentials
- OBS/VTube Studio endpoints
- LLM model/provider settings
- vision/audio settings
- AxelChat session directory

The example file uses generic placeholders and local defaults.

## Security

Sensitive data is filtered before it is persisted or passed between components where the filter is applicable. Platform messages and web results are treated as untrusted context for the LLM.

The runtime does not blindly execute a model-generated ban command. Moderation actions are gated by explicit application logic and configuration.

Do not commit .env, OAuth token files, vts_token.txt, runtime databases, logs, sessions or model binaries.

## Verification

CI covers import integrity, tests and source hygiene. Live authorization against Discord, Twitch, YouTube, Telegram, VTube Studio and OBS is environment-dependent and must be validated on the actual host.

## Known limitations

- Some integrations require external applications/services.
- Large voice/vision model binaries are intentionally outside Git.
- Performance depends on the chosen local models and hardware.
- A complete production deployment requires real credentials and live integration testing.

## Public snapshot

This repository contains the current refactor snapshot as a clean public source tree. Private runtime state, credentials and previous private Git history are not part of the public Git graph.
