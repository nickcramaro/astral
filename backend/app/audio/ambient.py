"""Ambient and SFX audio — generation and caching.

Uses the SFX provider (if available) for sound generation.
Falls back gracefully when no provider supports sound effects.
"""

import base64
import hashlib
import logging
from pathlib import Path

from app.audio.providers.base import VoiceProvider

log = logging.getLogger(__name__)

AUDIO_CACHE = Path(__file__).parent.parent.parent.parent / "audio-cache"


def _cache_key(prefix: str, description: str, provider_name: str) -> Path:
    """Build a cache file path from prefix, description hash, and provider."""
    desc_hash = hashlib.sha256(description.encode()).hexdigest()[:16]
    return AUDIO_CACHE / f"{prefix}_{provider_name}_{desc_hash}.mp3"


async def get_ambient(description: str, sfx_provider: VoiceProvider | None) -> str | None:
    """Get or generate an ambient audio loop for a scene description.

    Returns base64-encoded MP3 string, or None if no SFX provider available.
    """
    if sfx_provider is None:
        return None

    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_key("ambient", description, sfx_provider.name)

    if cache_path.exists():
        log.debug("Ambient cache hit: %s", description[:40])
        return base64.b64encode(cache_path.read_bytes()).decode("ascii")

    log.info("Generating ambient: %s", description[:60])
    audio_bytes = await sfx_provider.generate_sound_effect(description, 10.0)
    if audio_bytes is None:
        return None

    cache_path.write_bytes(audio_bytes)
    return base64.b64encode(audio_bytes).decode("ascii")


async def get_sfx(description: str, sfx_provider: VoiceProvider | None) -> str | None:
    """Get or generate a sound effect.

    Returns base64-encoded MP3 string, or None if no SFX provider available.
    """
    if sfx_provider is None:
        return None

    AUDIO_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = _cache_key("sfx", description, sfx_provider.name)

    if cache_path.exists():
        log.debug("SFX cache hit: %s", description[:40])
        return base64.b64encode(cache_path.read_bytes()).decode("ascii")

    log.info("Generating SFX: %s", description[:60])
    audio_bytes = await sfx_provider.generate_sound_effect(description, 3.0)
    if audio_bytes is None:
        return None

    cache_path.write_bytes(audio_bytes)
    return base64.b64encode(audio_bytes).decode("ascii")
