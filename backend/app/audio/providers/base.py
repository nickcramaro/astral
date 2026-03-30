"""Voice provider interface — abstract base for all TTS backends."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class VoiceInfo:
    """Metadata for a voice available from a provider."""

    voice_id: str
    name: str
    provider: str
    language_codes: list[str] = field(default_factory=list)
    preview_url: str | None = None
    cloned: bool = False


class VoiceProvider(ABC):
    """Common interface that all TTS providers implement."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier (e.g. 'elevenlabs', 'mistral', 'local')."""

    @abstractmethod
    async def generate_tts(
        self,
        text: str,
        voice_id: str,
        settings: dict | None = None,
    ) -> str | None:
        """Generate speech from text.

        Returns base64-encoded audio (MP3) or None on failure.
        """

    async def list_voices(self) -> list[VoiceInfo]:
        """List available voices. Override if supported."""
        return []

    async def clone_voice(
        self,
        name: str,
        audio_samples: list[bytes],
        description: str = "",
    ) -> VoiceInfo | None:
        """Clone a voice from audio samples. Returns None if unsupported."""
        return None

    async def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        """Get metadata for a specific voice. Override if supported."""
        return None

    def supports_cloning(self) -> bool:
        """Whether this provider supports voice cloning."""
        return False

    def supports_sound_effects(self) -> bool:
        """Whether this provider can generate ambient/SFX audio."""
        return False

    async def generate_sound_effect(
        self,
        description: str,
        duration_seconds: float,
    ) -> bytes | None:
        """Generate a sound effect from a text description.

        Returns raw audio bytes or None if unsupported.
        """
        return None
