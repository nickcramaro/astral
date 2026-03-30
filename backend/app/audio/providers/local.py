"""Local Voxtral TTS provider.

Runs Voxtral 4B locally via vLLM, llama.cpp, or compatible inference server.
Zero-cost TTS for local gameplay. Expects an OpenAI-compatible TTS endpoint.
"""

import asyncio
import base64
import logging
import os

import httpx

from app.audio.providers.base import VoiceInfo, VoiceProvider

log = logging.getLogger(__name__)

DEFAULT_LOCAL_URL = "http://localhost:8080"


class LocalVoiceProvider(VoiceProvider):
    """Local inference server running Voxtral 4B (or compatible TTS model)."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str = "voxtral-mini",
    ):
        self._base_url = (base_url or os.getenv("LOCAL_TTS_URL", DEFAULT_LOCAL_URL)).rstrip("/")
        self._model = model
        self._client: httpx.AsyncClient | None = None

    @property
    def name(self) -> str:
        return "local"

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=30.0,
            )
        return self._client

    async def generate_tts(
        self, text: str, voice_id: str, settings: dict | None = None,
    ) -> str | None:
        client = self._get_client()

        try:
            # OpenAI-compatible TTS endpoint (used by vLLM, llama.cpp, etc.)
            payload: dict = {
                "model": self._model,
                "input": text,
                "voice": voice_id,
                "response_format": "mp3",
            }
            if settings and "speed" in settings:
                payload["speed"] = settings["speed"]

            response = await client.post("/v1/audio/speech", json=payload)
            response.raise_for_status()
            return base64.b64encode(response.content).decode("ascii")
        except httpx.ConnectError:
            log.warning("Local TTS server not reachable at %s", self._base_url)
            return None
        except Exception:
            log.exception("Local TTS failed for voice %s", voice_id)
            return None

    async def list_voices(self) -> list[VoiceInfo]:
        client = self._get_client()
        try:
            response = await client.get("/v1/audio/voices")
            response.raise_for_status()
            data = response.json()
            return [
                VoiceInfo(
                    voice_id=v["id"],
                    name=v.get("name", v["id"]),
                    provider=self.name,
                    cloned=v.get("type") == "cloned",
                )
                for v in data.get("voices", data.get("data", []))
            ]
        except httpx.ConnectError:
            log.warning("Local TTS server not reachable at %s", self._base_url)
            return []
        except Exception:
            log.exception("Failed to list local voices")
            return []

    async def clone_voice(
        self, name: str, audio_samples: list[bytes], description: str = "",
    ) -> VoiceInfo | None:
        """Clone a voice locally — uploads sample to local server."""
        client = self._get_client()
        try:
            files = [
                ("files", (f"sample_{i}.wav", sample, "audio/wav"))
                for i, sample in enumerate(audio_samples)
            ]
            # Use a fresh client for multipart (no base_url content-type conflict)
            async with httpx.AsyncClient(timeout=60.0) as upload_client:
                response = await upload_client.post(
                    f"{self._base_url}/v1/audio/voices/clone",
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
        except httpx.ConnectError:
            log.warning("Local TTS server not reachable at %s", self._base_url)
            return None
        except Exception:
            log.exception("Local voice cloning failed")
            return None

    def supports_cloning(self) -> bool:
        return True

    async def health_check(self) -> bool:
        """Check if the local inference server is running."""
        try:
            client = self._get_client()
            response = await client.get("/health")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
