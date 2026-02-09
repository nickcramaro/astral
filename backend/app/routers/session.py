"""WebSocket gameplay session."""

import json
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.orchestrator.dm import DMOrchestrator

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

    # Initialize orchestrator for this session
    dm = DMOrchestrator(campaign_dir=campaign_dir, data_dir=DATA_DIR)

    # Send initial state
    char_path = campaign_dir / "character.json"
    if char_path.exists():
        char = json.loads(char_path.read_text())
        await websocket.send_json({"type": "state", "updates": char})

    await websocket.send_json({"type": "text", "content": "[Connected to campaign. What do you do?]"})

    try:
        while True:
            data = await websocket.receive_json()
            player_message = data.get("message", "")
            if not player_message.strip():
                continue

            # Run DM turn and stream results
            async for msg in dm.run_turn(player_message):
                await websocket.send_json(msg)

    except WebSocketDisconnect:
        pass
