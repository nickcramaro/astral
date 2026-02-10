"""ElevenLabs streaming TTS integration."""

import asyncio
import base64
import logging
import os

from elevenlabs import ElevenLabs

log = logging.getLogger(__name__)

_client: ElevenLabs | None = None


def _get_client() -> ElevenLabs | None:
    """Lazy-init singleton ElevenLabs client."""
    global _client
    if _client is None:
        api_key = os.getenv("ELEVENLABS_API_KEY")
        if not api_key:
            log.warning("ELEVENLABS_API_KEY not set — TTS disabled")
            return None
        _client = ElevenLabs(api_key=api_key)
    return _client


def _generate_sync(
    text: str,
    voice_id: str,
    voice_settings: dict | None = None,
) -> bytes | None:
    """Blocking call to ElevenLabs TTS. Run via asyncio.to_thread()."""
    client = _get_client()
    if not client:
        return None

    try:
        kwargs: dict = {
            "text": text,
            "voice_id": voice_id,
            "model_id": "eleven_multilingual_v2",
            "output_format": "mp3_44100_128",
        }
        if voice_settings:
            from elevenlabs import VoiceSettings
            kwargs["voice_settings"] = VoiceSettings(
                stability=voice_settings.get("stability", 0.5),
                similarity_boost=voice_settings.get("similarity_boost", 0.75),
                style=voice_settings.get("style", 0.0),
            )

        audio_iter = client.text_to_speech.convert(**kwargs)

        # Accumulate all chunks into one buffer
        chunks = []
        for chunk in audio_iter:
            chunks.append(chunk)
        return b"".join(chunks)
    except Exception:
        log.exception("TTS generation failed for voice %s", voice_id)
        return None


async def generate_tts(
    text: str,
    voice_id: str,
    voice_settings: dict | None = None,
) -> str | None:
    """Generate TTS audio and return as base64 string, or None on failure.

    Runs the sync ElevenLabs SDK call in a thread to avoid blocking the event loop.
    """
    audio_bytes = await asyncio.to_thread(_generate_sync, text, voice_id, voice_settings)
    if audio_bytes is None:
        return None
    return base64.b64encode(audio_bytes).decode("ascii")
