"""Shared fixtures for audio provider tests."""

import base64
from unittest.mock import AsyncMock

import pytest

from app.audio.providers.base import VoiceInfo, VoiceProvider


class FakeVoiceProvider(VoiceProvider):
    """In-memory provider for testing. Returns deterministic audio data."""

    def __init__(self, name_override: str = "fake"):
        self._name = name_override
        self.tts_calls: list[dict] = []
        self.sfx_calls: list[dict] = []
        self._fail_tts = False
        self._fail_sfx = False
        self._supports_sfx = False

    @property
    def name(self) -> str:
        return self._name

    async def generate_tts(
        self, text: str, voice_id: str, settings: dict | None = None,
    ) -> str | None:
        self.tts_calls.append({"text": text, "voice_id": voice_id, "settings": settings})
        if self._fail_tts:
            return None
        # Return base64 of a deterministic "audio" payload
        payload = f"audio:{voice_id}:{text[:20]}".encode()
        return base64.b64encode(payload).decode("ascii")

    def supports_sound_effects(self) -> bool:
        return self._supports_sfx

    async def generate_sound_effect(
        self, description: str, duration_seconds: float,
    ) -> bytes | None:
        self.sfx_calls.append({"description": description, "duration": duration_seconds})
        if self._fail_sfx:
            return None
        return f"sfx:{description[:20]}".encode()

    async def list_voices(self) -> list[VoiceInfo]:
        return [
            VoiceInfo(voice_id="fake-001", name="FakeVoice", provider=self._name),
        ]


@pytest.fixture
def fake_provider():
    """A fresh FakeVoiceProvider instance."""
    return FakeVoiceProvider()


@pytest.fixture
def fake_sfx_provider():
    """A FakeVoiceProvider with sound effects enabled."""
    p = FakeVoiceProvider(name_override="fake_sfx")
    p._supports_sfx = True
    return p


@pytest.fixture
def tmp_campaign(tmp_path):
    """Create a minimal campaign directory with a voice registry."""
    import json

    campaign = tmp_path / "campaigns" / "test-campaign"
    campaign.mkdir(parents=True)

    # Legacy format registry (flat, ElevenLabs-style)
    registry = {
        "narrator": {
            "voice_id": "narrator-voice-001",
            "voice_name": "Narrator",
            "settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        "npcs": {
            "Gandalf": {
                "voice_id": "gandalf-voice-001",
                "voice_name": "Gandalf",
                "settings": {"stability": 0.6, "similarity_boost": 0.8},
            },
        },
        "ambience": {
            "Tavern": "busy tavern, crackling fireplace",
        },
    }
    (campaign / "voice-registry.json").write_text(json.dumps(registry))
    return campaign


@pytest.fixture
def multi_provider_campaign(tmp_path):
    """Campaign with multi-provider voice registry format."""
    import json

    campaign = tmp_path / "campaigns" / "multi-provider"
    campaign.mkdir(parents=True)

    registry = {
        "narrator": {
            "elevenlabs": {
                "voice_id": "el-narrator-001",
                "settings": {"stability": 0.5},
            },
            "mistral": {
                "voice_id": "mi-narrator-001",
                "settings": {"speed": 1.0},
            },
            "local": {
                "voice_id": "local-narrator-001",
            },
        },
        "npcs": {
            "Gandalf": {
                "elevenlabs": {
                    "voice_id": "el-gandalf-001",
                    "settings": {"stability": 0.6},
                },
                "mistral": {
                    "voice_id": "mi-gandalf-001",
                },
            },
        },
        "ambience": {},
    }
    (campaign / "voice-registry.json").write_text(json.dumps(registry))
    return campaign
