"""WebSocket gameplay session."""

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.audio.pipeline import AudioPipeline
from app.orchestrator.dm import DMOrchestrator

log = logging.getLogger(__name__)

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


@router.websocket("/ws/session/{campaign_id}")
async def session_ws(websocket: WebSocket, campaign_id: str):
    """Main gameplay WebSocket — player messages in, DM responses out."""
    await websocket.accept()

    campaign_dir = DATA_DIR / "campaigns" / campaign_id
    if not campaign_dir.is_dir():
        await websocket.send_json({"type": "error", "content": f"Campaign '{campaign_id}' not found"})
        await websocket.close()
        return

    # Initialize orchestrator and audio pipeline
    dm = DMOrchestrator(campaign_dir=campaign_dir, data_dir=DATA_DIR)
    audio = AudioPipeline(campaign_dir=campaign_dir)
    audio_task: asyncio.Task | None = None

    # Send initial state
    char_path = campaign_dir / "character.json"
    if char_path.exists():
        char = json.loads(char_path.read_text())
        await websocket.send_json({"type": "state", "updates": char})

    # Generate an opening DM turn — recap if there's session history, otherwise fresh start
    log_path = campaign_dir / "session-log.md"
    has_history = False
    if log_path.exists():
        log_text = log_path.read_text().strip()
        # Check for actual session content beyond the boilerplate header
        has_history = "### Session Ended:" in log_text

    if has_history:
        opening_prompt = (
            "[System] The player has reconnected. Give a brief, atmospheric recap of where "
            "they are and what just happened based on the session log. Set the scene, remind "
            "them of their situation, and end with a prompt for action. Use your inline markers."
        )
    else:
        opening_prompt = (
            "[System] This is the start of a new campaign. Set the opening scene — describe "
            "where the player character is, what's happening around them, and draw them into "
            "the story. Use your inline markers."
        )

    raw_texts: list[str] = []
    async for msg in dm.run_turn(opening_prompt):
        raw = msg.pop("_raw", None)
        await websocket.send_json(msg)
        if raw:
            raw_texts.append(raw)

    if raw_texts:
        full_raw = "\n\n".join(raw_texts)
        audio_task = asyncio.create_task(
            _generate_audio(websocket, audio, full_raw)
        )

    try:
        while True:
            data = await websocket.receive_json()

            # Handle audio mode changes
            if data.get("type") == "set_audio_mode":
                mode = data.get("mode", "full")
                audio.set_mode(mode)
                log.info("Audio mode set to: %s", mode)
                continue

            player_message = data.get("message", "")
            if not player_message.strip():
                continue

            # Cancel any in-flight audio generation from the previous turn
            if audio_task and not audio_task.done():
                audio_task.cancel()

            # Run DM turn and stream text results immediately
            raw_texts: list[str] = []
            async for msg in dm.run_turn(player_message):
                # Extract raw text before sending (don't leak to client)
                raw = msg.pop("_raw", None)
                await websocket.send_json(msg)
                if raw:
                    raw_texts.append(raw)

            # Spawn background audio generation for the full turn
            if raw_texts:
                full_raw = "\n\n".join(raw_texts)
                audio_task = asyncio.create_task(
                    _generate_audio(websocket, audio, full_raw)
                )

    except WebSocketDisconnect:
        # Cancel audio on disconnect
        if audio_task and not audio_task.done():
            audio_task.cancel()


async def _generate_audio(websocket: WebSocket, pipeline: AudioPipeline, raw_text: str) -> None:
    """Background task: parse raw DM text, generate audio, send over WebSocket."""
    try:
        async for msg in pipeline.process_text(raw_text):
            await websocket.send_json(msg)
    except asyncio.CancelledError:
        pass
    except Exception:
        log.exception("Audio generation failed")
