# Vexa

Local AI streamer runtime using Ollama, Silero TTS, Whisper STT, screen vision, VTube Studio, Discord voice receive, Telegram and AxelChat.

## Setup
Copy .env.example to .env and fill local credentials.
Install requirements.txt.
Start Ollama and make sure the configured model exists.
Install FFmpeg for Discord playback.
Run python main.py.

The Silero V5 model is not stored in Git. It is downloaded from the official model URL when enabled.
Runtime database, logs, WAV files, Telegram sessions and VTS token are ignored by Git.

## Discord
Commands: !зайди, !слушай, !перестаньслушать, !выйди.
Discord voice receive uses discord-ext-voice-recv. It is a pre-release dependency, so pinning is intentional.

## Verification
python -m compileall .
python -m pytest -q

Live authorization and service integration require a real host environment with Ollama, Discord, Telegram and VTube Studio.
