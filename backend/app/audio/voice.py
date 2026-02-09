"""ElevenLabs streaming TTS integration."""


async def stream_tts(text: str, voice_id: str):
    """Stream TTS audio bytes from ElevenLabs.

    Yields audio chunks as bytes for forwarding to the client via WebSocket.
    """
    # TODO: Implement ElevenLabs streaming API call
    # - Use websocket or HTTP streaming endpoint
    # - Yield audio bytes as they arrive
    pass
