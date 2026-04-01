# Astral

AI game master platform for solo D&D sessions with streamed narration, NPC voices, and ambient audio. Powered by Claude for storytelling and ElevenLabs (or other providers) for text-to-speech.

## Features

- **AI Dungeon Master** — Claude-powered DM with tool use for dice rolls, combat, inventory, and more
- **Streamed narration** — Real-time text and audio streaming over WebSocket
- **NPC voices** — Distinct TTS voices per character
- **Ambient audio & SFX** — AI-generated soundscapes and sound effects
- **Campaign import** — PDF/DOCX adventure modules parsed via RAG pipeline
- **Character sheets** — Interactive character management in the browser
- **Multiple TTS providers** — ElevenLabs, Mistral Voxtral, or local TTS server

## Quick Start

### Prerequisites

- Python 3.11+ and [uv](https://docs.astral.sh/uv/)
- [Bun](https://bun.sh/)
- API keys for [Anthropic](https://console.anthropic.com/) and [ElevenLabs](https://elevenlabs.io/) (or another TTS provider)

### Setup

```bash
# Clone and configure
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# Backend
cd backend
uv sync
uv run uvicorn app.main:app --reload

# Frontend (in another terminal)
cd frontend
bun install
bun dev
```

Frontend runs on http://localhost:5173, backend on http://localhost:8000.

## Architecture

```
backend/          FastAPI (Python 3.11+, uv)
├── app/
│   ├── main.py              Entry point
│   ├── routers/             HTTP + WebSocket endpoints
│   ├── orchestrator/        DM agent (Claude API tool-use loop)
│   │   ├── dm.py            Main DM turn loop
│   │   ├── tools.py         Tool schemas for Claude
│   │   ├── parser.py        Inline marker parser
│   │   └── prompts/         System prompts + specialist templates
│   ├── audio/               TTS providers + ambient/SFX
│   ├── game/                Game state managers
│   ├── import_pipeline/     PDF → RAG → campaign extraction
│   └── features/            D&D 5e API integrations
├── data/campaigns/          Campaign state (JSON files)
└── audio-cache/             Generated audio files

frontend/         React + TypeScript (Vite, bun)
├── src/
│   ├── components/          UI components (Chat, CharacterSheet, etc.)
│   ├── hooks/               useSession, useAudio, useImport
│   ├── audio/               Web Audio API engine
│   └── types/               Shared TypeScript types
```

## How It Works

1. The player sends a message over WebSocket
2. The **DM orchestrator** streams a response from Claude, using tools for game mechanics (dice rolls, combat, inventory, etc.)
3. An **inline marker parser** splits the stream into segments: `[NARRATE]` for narration, `[NPC:name]` for character dialogue, `[AMBIENT:desc]` for background audio, `[SFX:desc]` for sound effects
4. Each segment is routed to the appropriate TTS voice or audio generator
5. Audio streams back to the browser across three channels (voice, ambient, SFX) via the Web Audio API

## Environment Variables

Copy `backend/.env.example` to `backend/.env`:

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API key |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `CLAUDE_MODEL` | Model for DM orchestrator (default: `claude-sonnet-4-5-20250929`) |
| `VOICE_PROVIDER` | TTS provider: `elevenlabs`, `mistral`, or `local` |
| `MISTRAL_API_KEY` | Mistral API key (if using Voxtral) |
| `LOCAL_TTS_URL` | Local TTS server URL (if using local provider) |
| `SFX_PROVIDER` | SFX/ambient provider (defaults to `VOICE_PROVIDER`) |

## License

Private.
