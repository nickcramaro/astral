"""Ambient and SFX audio — generation and caching."""

import asyncio
import base64
import hashlib
import logging
from pathlib import Path

from elevenlabs import ElevenLabs

log = logging.getLogger(__name__)

AUDIO_CACHE = Path(__file__).parent.parent.parent.parent / "audio-cache"


def _cache_key(prefix: str, description: str) -> Path:
    """Build a cache file path from prefix and description hash."""
    desc_hash = hashlib.sha256(description.encode()).hexdigest()[:16]
    return AUDIO_CACHE / f"{prefix}_{desc_hash}.mp3"


def _generate_sound_sync(
    description: str,
    duration_seconds: float,
) -> bytes | None:
    """Blocking call to ElevenLabs sound effects API."""
    import os
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None

    try:
        client = ElevenLabs(api_key=api_key)
        result = client.text_to_sound_effects.convert(
            text=description,
            duration_seconds=duration_seconds,
        )
        # Result is an iterator of bytes
        chunks = []
        for chunk in result:
            chunks.append(chunk)
        return b"".join(chunks)
    except Exception:
        log.exception("Sound generation failed: %s", description)
        return None


async def get_ambient(description: str) -> str | None:
    """Get or generate an ambient audio loop for a scene description.

    Checks cache first, generates via ElevenLabs sound generation if missing.
    Returns base64-encoded MP3 string, or None on failure.
    """
    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_key("ambient", description)

    if cache_path.exists():
        log.debug("Ambient cache hit: %s", description[:40])
        return base64.b64encode(cache_path.read_bytes()).decode("ascii")

    log.info("Generating ambient: %s", description[:60])
    audio_bytes = await asyncio.to_thread(_generate_sound_sync, description, 10.0)
    if audio_bytes is None:
        return None

    cache_path.write_bytes(audio_bytes)
    return base64.b64encode(audio_bytes).decode("ascii")


async def get_sfx(description: str) -> str | None:
    """Get or generate a sound effect.

    Checks cache first, generates via ElevenLabs if missing.
    Returns base64-encoded MP3 string, or None on failure.
    """
    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_key("sfx", description)

    if cache_path.exists():
        log.debug("SFX cache hit: %s", description[:40])
        return base64.b64encode(cache_path.read_bytes()).decode("ascii")

    log.info("Generating SFX: %s", description[:60])
    audio_bytes = await asyncio.to_thread(_generate_sound_sync, description, 3.0)
    if audio_bytes is None:
        return None

    cache_path.write_bytes(audio_bytes)
    return base64.b64encode(audio_bytes).decode("ascii")
