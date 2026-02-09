"""WebSocket gameplay session."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws/session/{campaign_id}")
async def session_ws(websocket: WebSocket, campaign_id: str):
    """Main gameplay WebSocket — player messages in, DM responses out."""
    await websocket.accept()

    # TODO: Load campaign state, init DM orchestrator
    try:
        while True:
            data = await websocket.receive_json()
            player_message = data.get("message", "")

            # TODO: Run DM orchestrator, stream text + audio + state
            await websocket.send_json({
                "type": "text",
                "content": f"[DM stub] You said: {player_message}",
            })
    except WebSocketDisconnect:
        pass
