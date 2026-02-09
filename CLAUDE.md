# Astral

AI game master platform — solo D&D sessions with streamed narration, NPC voices, and ambient audio.

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
│   ├── audio/               ElevenLabs TTS + ambient/SFX
│   ├── game/                Game state managers (copied from dm-claude-voice)
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

## Development

```bash
# Backend
cd backend && uv run uvicorn app.main:app --reload

# Frontend
cd frontend && bun dev
```

Frontend runs on :5173, backend on :8000. CORS configured for local dev.

## Key Patterns

- **DM orchestrator**: Claude API streaming with tool use. Tools wrap game managers.
- **Inline markers**: DM output uses `[NARRATE]`, `[NPC:name]`, `[AMBIENT:desc]`, `[SFX:desc]` markers. Backend parser splits stream and routes to TTS/audio.
- **WebSocket session**: Single WS connection per session. Three message types: `text`, `audio`, `state`.
- **Game state**: JSON files per campaign in `data/campaigns/{name}/`. Managers read/write directly.
- **Audio**: ElevenLabs streaming TTS. Three browser channels (voice, ambient, SFX) via Web Audio API.

## Env Vars

Copy `backend/.env.example` → `backend/.env`:
- `ANTHROPIC_API_KEY` — Claude API
- `ELEVENLABS_API_KEY` — TTS and sound generation
- `CLAUDE_MODEL` — Model for DM orchestrator (default: claude-sonnet-4-5-20250929)

## Origin

Game managers, RAG pipeline, and D&D features copied from `dm-claude-voice` and adapted for web. Specialist agent prompts in `orchestrator/prompts/specialists/` converted from Claude Code agent format.
