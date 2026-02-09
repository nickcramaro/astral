"""Ambient and SFX audio — generation and caching."""

from pathlib import Path

AUDIO_CACHE = Path(__file__).parent.parent.parent.parent / "audio-cache"


async def get_ambient(description: str) -> bytes | None:
    """Get or generate an ambient audio loop for a scene description.

    Checks cache first, generates via ElevenLabs sound generation if missing.
    """
    # TODO: Implement cache lookup + ElevenLabs sound generation
    return None


async def get_sfx(description: str) -> bytes | None:
    """Get or generate a sound effect.

    Checks cache first, generates via ElevenLabs if missing.
    """
    # TODO: Implement cache lookup + generation
    return None
