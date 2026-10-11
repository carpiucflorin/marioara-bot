# Marioara Bot

Marioara is a local personal AI companion that combines memory, emotional tone, topic tracking, safety filtering, and local Ollama generation.

## Features
- Local context-aware replies using Ollama
- SQLite-backed memory for messages, facts, preferences, episodes, and snapshots
- Emotional and behavior-aware response tuning
- User tone and state detection
- Basic safety and jailbreak filtering
- Tkinter chat interface
- Optional Windows TTS using `edge-tts` + `ffmpeg`

## Project structure

```text
marioara-bot/
├── advanced_bot_system.py
├── behavior_engine.py
├── bot_memory.json
├── chat_interface.py
├── test_behavior_modules.py
├── user_state_detector.py
├── voice.py
├── speaker.py
├── core/
│   ├── __init__.py
│   ├── background_worker.py
│   ├── intent_classifier.py
│   ├── planner.py
│   ├── pipeline.py
│   ├── prompt_builder.py
│   ├── safety.py
│   ├── tool_router.py
│   └── __init__.py
├── conversation/
│   ├── __init__.py
│   ├── coherence_buffer.py
│   └── initiative.py
├── memory/
│   ├── __init__.py
│   ├── db.py
│   ├── extract.py
│   └── store.py
├── README.md
├── requirements.txt
├── .gitignore
├── FEATURES.md
├── INTEGRATION.md
├── QUICK_REFERENCE.md
└── .venv/
```

## Quick start

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start Ollama locally and make sure a model is installed, for example:

```bash
ollama pull llama3
```

4. Start the app:

```bash
python chat_interface.py
```

Optional environment variables:

```bash
export MARIOARA_OLLAMA_URL=http://localhost:11434
export MARIOARA_OLLAMA_MODEL=llama3
```

## Notes
- The app expects a local Ollama server.
- Voice output depends on `ffmpeg` and `edge-tts`.
- `bot_memory.json` is treated as a legacy import source; the active memory store is SQLite.

## License
This project is provided for local development and experimentation.
