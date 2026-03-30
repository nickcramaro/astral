"""Backwards-compatible TTS entry point.

Delegates to the configured voice provider. Existing code that imports
generate_tts from here will continue to work.
"""

from app.audio.providers import get_voice_provider


async def generate_tts(
    text: str,
    voice_id: str,
    voice_settings: dict | None = None,
) -> str | None:
    """Generate TTS audio via the configured provider. Returns base64 MP3 or None."""
    provider = get_voice_provider()
    return await provider.generate_tts(text, voice_id, voice_settings)
