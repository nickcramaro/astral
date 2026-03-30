"""ElevenLabs TTS provider."""

import asyncio
import base64
import logging
import os

from app.audio.providers.base import VoiceInfo, VoiceProvider

log = logging.getLogger(__name__)


class ElevenLabsProvider(VoiceProvider):
    """ElevenLabs API — high-quality TTS with voice cloning and sound effects."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("ELEVENLABS_API_KEY")
        self._client = None

    @property
    def name(self) -> str:
        return "elevenlabs"

    def _get_client(self):
        """Lazy-init the ElevenLabs SDK client."""
        if self._client is None:
            if not self._api_key:
                log.warning("ELEVENLABS_API_KEY not set — ElevenLabs TTS disabled")
                return None
            from elevenlabs import ElevenLabs
            self._client = ElevenLabs(api_key=self._api_key)
        return self._client

    def _generate_sync(
        self, text: str, voice_id: str, settings: dict | None = None,
    ) -> bytes | None:
        """Blocking call to ElevenLabs TTS."""
        client = self._get_client()
        if not client:
            return None

        try:
            kwargs: dict = {
                "text": text,
                "voice_id": voice_id,
                "model_id": "eleven_multilingual_v2",
                "output_format": "mp3_44100_128",
            }
            if settings:
                from elevenlabs import VoiceSettings
                kwargs["voice_settings"] = VoiceSettings(
                    stability=settings.get("stability", 0.5),
                    similarity_boost=settings.get("similarity_boost", 0.75),
                    style=settings.get("style", 0.0),
                )

            audio_iter = client.text_to_speech.convert(**kwargs)
            chunks = []
            for chunk in audio_iter:
                chunks.append(chunk)
            return b"".join(chunks)
        except Exception:
            log.exception("ElevenLabs TTS failed for voice %s", voice_id)
            return None

    async def generate_tts(
        self, text: str, voice_id: str, settings: dict | None = None,
    ) -> str | None:
        audio_bytes = await asyncio.to_thread(self._generate_sync, text, voice_id, settings)
        if audio_bytes is None:
            return None
        return base64.b64encode(audio_bytes).decode("ascii")

    async def list_voices(self) -> list[VoiceInfo]:
        client = self._get_client()
        if not client:
            return []
        try:
            response = await asyncio.to_thread(client.voices.get_all)
            return [
                VoiceInfo(
                    voice_id=v.voice_id,
                    name=v.name,
                    provider=self.name,
                    cloned=v.category == "cloned",
                )
                for v in response.voices
            ]
        except Exception:
            log.exception("Failed to list ElevenLabs voices")
            return []

    async def clone_voice(
        self, name: str, audio_samples: list[bytes], description: str = "",
    ) -> VoiceInfo | None:
        client = self._get_client()
        if not client:
            return None
        try:
            voice = await asyncio.to_thread(
                client.clone.create,
                name=name,
                description=description,
                files=audio_samples,
            )
            return VoiceInfo(
                voice_id=voice.voice_id,
                name=voice.name,
                provider=self.name,
                cloned=True,
            )
        except Exception:
            log.exception("ElevenLabs voice cloning failed")
            return None

    def supports_cloning(self) -> bool:
        return True

    def supports_sound_effects(self) -> bool:
        return True

    def _generate_sound_sync(
        self, description: str, duration_seconds: float,
    ) -> bytes | None:
        """Blocking call to ElevenLabs sound effects API."""
        client = self._get_client()
        if not client:
            return None
        try:
            result = client.text_to_sound_effects.convert(
                text=description,
                duration_seconds=duration_seconds,
            )
            chunks = []
            for chunk in result:
                chunks.append(chunk)
            return b"".join(chunks)
        except Exception:
            log.exception("ElevenLabs sound generation failed: %s", description)
            return None

    async def generate_sound_effect(
        self, description: str, duration_seconds: float,
    ) -> bytes | None:
        return await asyncio.to_thread(
            self._generate_sound_sync, description, duration_seconds,
        )
