"""WebSocket gameplay session."""

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.audio.pipeline import AudioPipeline
from app.audio.streaming import StreamingAudioBuffer
from app.orchestrator.dm import DMOrchestrator

log = logging.getLogger(__name__)

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _roll_result_msg(result: dict) -> dict:
    """Build a roll_result WS message, remapping dice 'type' to 'roll_type'."""
    msg = {"type": "roll_result"}
    for k, v in result.items():
        msg["roll_type" if k == "type" else k] = v
    return msg

CACHE_FILE = "opening-cache.json"


def _session_log_hash(campaign_dir: Path) -> str:
    """Hash the session log content to detect changes."""
    log_path = campaign_dir / "session-log.md"
    if not log_path.exists():
        return ""
    return hashlib.sha256(log_path.read_bytes()).hexdigest()


def _load_opening_cache(campaign_dir: Path, current_hash: str) -> list[dict] | None:
    """Load cached opening messages if the session log hasn't changed."""
    cache_path = campaign_dir / CACHE_FILE
    if not cache_path.exists():
        return None
    try:
        cache = json.loads(cache_path.read_text())
        if cache.get("session_log_hash") == current_hash:
            return cache.get("messages", [])
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_opening_cache(campaign_dir: Path, current_hash: str, messages: list[dict]) -> None:
    """Save opening messages to cache."""
    cache_path = campaign_dir / CACHE_FILE
    cache_path.write_text(json.dumps({
        "session_log_hash": current_hash,
        "messages": messages,
    }))


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
    audio_buf: StreamingAudioBuffer | None = None

    # WebSocket lock — main loop and audio drain task both write
    ws_lock = asyncio.Lock()

    async def ws_send(msg: dict):
        async with ws_lock:
            await websocket.send_json(msg)

    # Send initial state
    char_path = campaign_dir / "character.json"
    if char_path.exists():
        char = json.loads(char_path.read_text())
        await websocket.send_json({"type": "state", "updates": char})

    # Opening turn — serve from cache if session log hasn't changed
    log_hash = _session_log_hash(campaign_dir)
    cached = _load_opening_cache(campaign_dir, log_hash)

    if cached is not None:
        log.info("Opening cache HIT for %s — replaying %d messages", campaign_id, len(cached))
        # Replay cached text + audio messages
        for msg in cached:
            await websocket.send_json(msg)
        # Seed the DM conversation history with the cached text so follow-up turns have context
        cached_text = " ".join(m["content"] for m in cached if m.get("type") == "text")
        if cached_text:
            dm.messages.append({"role": "assistant", "content": [{"type": "text", "text": cached_text}]})
    else:
        log.info("Opening cache MISS for %s — generating fresh opening", campaign_id)
        # Generate fresh opening
        log_path = campaign_dir / "session-log.md"
        has_history = False
        if log_path.exists():
            log_text = log_path.read_text().strip()
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

        # Collect collapsed messages for cache (text + audio)
        opening_messages: list[dict] = []
        current_text = ""
        audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)

        async for msg in dm.run_turn(opening_prompt):
            if msg["type"] == "_raw_delta":
                audio_buf.feed(msg["content"])

            elif msg["type"] == "text_delta":
                current_text += msg["content"]
                await ws_send(msg)

            elif msg["type"] == "text_end":
                stripped = msg.get("content", "")
                await ws_send({"type": "text_end", "content": stripped})
                if stripped:
                    opening_messages.append({"type": "text", "content": stripped})
                    current_text = ""
                await audio_buf.flush()
                opening_messages.extend(audio_buf.sent_messages)
                # Fresh buffer for next content block
                audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)

            elif msg["type"] == "roll_request":
                if current_text:
                    opening_messages.append({"type": "text", "content": current_text})
                    current_text = ""
                await audio_buf.flush()
                opening_messages.extend(audio_buf.sent_messages)
                audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)
                await ws_send(msg)
                while True:
                    client_data = await websocket.receive_json()
                    if client_data.get("type") == "roll_execute":
                        break
                result = dm.tools.execute("roll_dice", {
                    "notation": msg["notation"],
                    "reason": msg.get("reason", ""),
                })
                await ws_send(_roll_result_msg(result))
                while True:
                    client_data = await websocket.receive_json()
                    if client_data.get("type") == "roll_ack":
                        break
                dm.resolve_roll(result)

            else:
                opening_messages.append(msg)
                await ws_send(msg)

        _save_opening_cache(campaign_dir, log_hash, opening_messages)
        audio_buf = None

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

            # Cancel any in-flight audio from the previous turn
            if audio_buf is not None:
                audio_buf.cancel()
            audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)

            # Run DM turn — stream clean text + feed raw deltas to audio buffer
            async for msg in dm.run_turn(player_message):
                if msg["type"] == "_raw_delta":
                    audio_buf.feed(msg["content"])

                elif msg["type"] == "text_delta":
                    await ws_send(msg)

                elif msg["type"] == "text_end":
                    await ws_send({"type": "text_end", "content": msg.get("content", "")})
                    await audio_buf.flush()
                    # Fresh buffer for next content block
                    audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)

                elif msg["type"] == "roll_request":
                    await audio_buf.flush()
                    audio_buf = StreamingAudioBuffer(pipeline=audio, send_fn=ws_send)
                    await ws_send(msg)

                    while True:
                        client_data = await websocket.receive_json()
                        if client_data.get("type") == "roll_execute":
                            break

                    result = dm.tools.execute("roll_dice", {
                        "notation": msg["notation"],
                        "reason": msg.get("reason", ""),
                    })

                    await ws_send(_roll_result_msg(result))

                    while True:
                        client_data = await websocket.receive_json()
                        if client_data.get("type") == "roll_ack":
                            break

                    dm.resolve_roll(result)
                else:
                    await ws_send(msg)

    except WebSocketDisconnect:
        if audio_buf is not None:
            audio_buf.cancel()
