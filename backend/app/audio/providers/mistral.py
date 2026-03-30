"""Mistral Voxtral TTS provider.

Uses Mistral's TTS API — significantly cheaper than ElevenLabs ($16/1M chars
vs $60-120/1M). Supports voice cloning from 2-3 second audio samples,
9 languages, and ~70ms latency.
"""

import asyncio
import base64
import logging
import os

import httpx

from app.audio.providers.base import VoiceInfo, VoiceProvider

log = logging.getLogger(__name__)

MISTRAL_TTS_URL = "https://api.mistral.ai/v1/audio/speech"
MISTRAL_VOICES_URL = "https://api.mistral.ai/v1/audio/voices"


class MistralVoiceProvider(VoiceProvider):
    """Mistral Voxtral API — cost-effective TTS with native voice cloning."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "mistral-tts-latest",
    ):
        self._api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self._model = model
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "mistral"

    def _get_client(self) -> httpx.AsyncClient | None:
        if not self._api_key:
            log.warning("MISTRAL_API_KEY not set — Mistral TTS disabled")
            return None
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def generate_tts(
        self, text: str, voice_id: str, settings: dict | None = None,
    ) -> str | None:
        client = self._get_client()
        if not client:
            return None

        try:
            payload: dict = {
                "model": self._model,
                "input": text,
                "voice": voice_id,
                "response_format": "mp3",
            }
            # Voxtral supports speed adjustment
            if settings and "speed" in settings:
                payload["speed"] = settings["speed"]

            response = await client.post(MISTRAL_TTS_URL, json=payload)
            response.raise_for_status()
            return base64.b64encode(response.content).decode("ascii")
        except Exception:
            log.exception("Mistral TTS failed for voice %s", voice_id)
            return None

    async def list_voices(self) -> list[VoiceInfo]:
        client = self._get_client()
        if not client:
            return []
        try:
            response = await client.get(MISTRAL_VOICES_URL)
            response.raise_for_status()
            data = response.json()
            return [
                VoiceInfo(
                    voice_id=v["id"],
                    name=v.get("name", v["id"]),
                    provider=self.name,
                    language_codes=v.get("languages", []),
                    cloned=v.get("type") == "cloned",
                )
                for v in data.get("voices", data.get("data", []))
            ]
        except Exception:
            log.exception("Failed to list Mistral voices")
            return []

    async def clone_voice(
        self, name: str, audio_samples: list[bytes], description: str = "",
    ) -> VoiceInfo | None:
        """Clone a voice from 2-3 second audio samples via Mistral API."""
        client = self._get_client()
        if not client:
            return None

        try:
            # Mistral voice cloning: upload audio sample(s), get a voice reference
            files = [
                ("files", (f"sample_{i}.wav", sample, "audio/wav"))
                for i, sample in enumerate(audio_samples)
            ]
            # Use a separate client for multipart upload
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=60.0,
            ) as upload_client:
                response = await upload_client.post(
                    f"{MISTRAL_VOICES_URL}/clone",
                    files=files,
                    data={"name": name, "description": description},
                )
                response.raise_for_status()
                data = response.json()
                return VoiceInfo(
                    voice_id=data["id"],
                    name=data.get("name", name),
                    provider=self.name,
                    cloned=True,
                )
        except Exception:
            log.exception("Mistral voice cloning failed")
            return None

    def supports_cloning(self) -> bool:
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
