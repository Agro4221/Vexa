# Vexa

Vexa is a local AI streamer runtime with configurable LLM access, voice I/O, optional screen vision, VTube Studio, Discord voice, Telegram, AxelChat, Twitch, YouTube, VK Play and OBS adapters.

## LLM independence

The chat LLM is deliberately model-agnostic. The code does not contain a named chat model. Set VEXA_MODEL to any compatible Ollama model, or leave it empty with OLLAMA_AUTO_SELECT_MODEL=true and let Vexa choose an installed model at runtime.

Vision is separate and has its own configurable model settings through VISION_MODEL_ID and VISION_MODEL_REVISION.

## Architecture

main.py is the runtime orchestrator. Event_Bus.py owns bounded priority events, Attention_Manager.py ranks attention, Vexa_State.py owns mutable runtime state, Core_Brain.py handles LLM requests, Memory_Core.py and Data_Base.py own persistent memory, Supervisor.py keeps background services alive, and platform modules isolate external services.

## Setup

Create a local .env from .env.example. Never commit real credentials, OAuth files, runtime databases, sessions or model binaries.

Install production dependencies:

    python -m pip install -r requirements.txt

Optional local microphone playback/recording:

    python -m pip install -r requirements-local-audio.txt

Start Ollama and install at least one chat model. Leave VEXA_MODEL empty for automatic selection, or set it explicitly for a particular deployment.

Install FFmpeg and run:

    python Health_Check.py
    python -m compileall -q .
    python -m pytest -q
    python main.py

## Integrations

Discord uses discord-ext-voice-recv for voice receive and FFmpeg for playback.

Twitch uses a dependency-free TLS IRC client for live chat and the Helix API for channel metadata.

YouTube uses OAuth 2.0 for Live Chat and broadcast management. The first authorization can open a local browser and stores its token under data/.

Telegram news uses a Telethon user session. social.py is a separate Telegram Bot API sender.

VTube Studio and OBS are optional integrations controlled by their *_ENABLED settings. VK Play is a configurable adapter and intentionally does not invent undocumented endpoints.

AxelChat watches messages.ini recursively and ignores old startup backlog by default.

## Vision and audio

Vision is lazy-loaded. On-demand analysis is triggered by chat/voice phrases and optional autonomous analysis is controlled with VISION_AUTONOMOUS=true and VISION_INTERVAL.

Whisper is lazy-loaded and keeps the source project's useful hot-word and hallucination filters. Silero TTS is lazy-loaded, serialized for concurrent use and writes unique temporary WAV files.

The supplied v5_ru.pt model is intentionally not stored in Git because it is a large binary. Put it at VOICE_MODEL_PATH or enable VOICE_AUTO_DOWNLOAD.

## Security

All service credentials are runtime configuration. AI moderation is a suggestion layer; the runtime does not execute a model-generated ban directly. Web results and platform messages are treated as untrusted context before reaching the LLM.

The repository is kept private during development and validation. Credentials shared during development should be rotated before real deployment.

## Verification

The test suite covers model selection, queueing, migration, action parsing, Twitch parsing, text cleanup, secret hygiene and import integrity.

Live authorization against Discord, Twitch, YouTube, Telegram, VTube Studio and OBS is host-dependent and must be exercised on the actual streaming machine.
