"""Voice provider factory — instantiates the configured TTS backend."""

import logging
import os

from app.audio.providers.base import VoiceInfo, VoiceProvider

log = logging.getLogger(__name__)

__all__ = ["VoiceProvider", "VoiceInfo", "get_voice_provider", "get_sfx_provider"]

# Singleton cache
_providers: dict[str, VoiceProvider] = {}


def get_voice_provider(name: str | None = None) -> VoiceProvider:
    """Get (or create) the voice provider for the given name.

    If name is None, reads VOICE_PROVIDER env var (default: 'elevenlabs').
    """
    name = (name or os.getenv("VOICE_PROVIDER", "elevenlabs")).lower()

    if name in _providers:
        return _providers[name]

    provider = _create_provider(name)
    _providers[name] = provider
    log.info("Voice provider initialized: %s", name)
    return provider


def get_sfx_provider() -> VoiceProvider | None:
    """Get the provider for ambient/SFX generation.

    Reads SFX_PROVIDER env var. Falls back to VOICE_PROVIDER.
    Returns None if the resolved provider doesn't support sound effects.
    """
    sfx_name = os.getenv("SFX_PROVIDER")
    provider = get_voice_provider(sfx_name)
    if provider.supports_sound_effects():
        return provider
    # If the main voice provider doesn't do SFX, try ElevenLabs as fallback
    if provider.name != "elevenlabs" and os.getenv("ELEVENLABS_API_KEY"):
        fallback = get_voice_provider("elevenlabs")
        if fallback.supports_sound_effects():
            log.info("SFX falling back to ElevenLabs (primary provider %s has no SFX)", provider.name)
            return fallback
    return None


def _create_provider(name: str) -> VoiceProvider:
    """Instantiate a provider by name."""
    if name == "elevenlabs":
        from app.audio.providers.elevenlabs import ElevenLabsProvider
        return ElevenLabsProvider()

    if name == "mistral":
        from app.audio.providers.mistral import MistralVoiceProvider
        return MistralVoiceProvider()

    if name == "local":
        from app.audio.providers.local import LocalVoiceProvider
        return LocalVoiceProvider()

    raise ValueError(
        f"Unknown voice provider: {name!r}. "
        f"Valid options: elevenlabs, mistral, local"
    )
