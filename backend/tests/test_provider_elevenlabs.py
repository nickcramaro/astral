"""Tests for the ElevenLabs provider."""

import base64
from unittest.mock import MagicMock, patch

import pytest

from app.audio.providers.elevenlabs import ElevenLabsProvider


class TestElevenLabsProvider:
    def test_name(self):
        provider = ElevenLabsProvider(api_key="test-key")
        assert provider.name == "elevenlabs"

    def test_supports_cloning(self):
        provider = ElevenLabsProvider(api_key="test-key")
        assert provider.supports_cloning() is True

    def test_supports_sound_effects(self):
        provider = ElevenLabsProvider(api_key="test-key")
        assert provider.supports_sound_effects() is True

    def test_no_api_key_returns_none_for_client(self):
        provider = ElevenLabsProvider(api_key=None)
        # Patch env to be empty too
        with patch.dict("os.environ", {}, clear=True):
            provider._api_key = None
            client = provider._get_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_generate_tts_no_api_key(self):
        provider = ElevenLabsProvider(api_key=None)
        provider._api_key = None
        result = await provider.generate_tts("hello", "voice-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_tts_calls_sdk(self):
        provider = ElevenLabsProvider(api_key="test-key")
        fake_audio = b"fake-mp3-data"

        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([fake_audio])
        provider._client = mock_client

        result = await provider.generate_tts("Hello world", "voice-123")

        assert result is not None
        assert base64.b64decode(result) == fake_audio
        mock_client.text_to_speech.convert.assert_called_once()
        call_kwargs = mock_client.text_to_speech.convert.call_args[1]
        assert call_kwargs["text"] == "Hello world"
        assert call_kwargs["voice_id"] == "voice-123"
        assert call_kwargs["model_id"] == "eleven_multilingual_v2"

    @pytest.mark.asyncio
    async def test_generate_tts_with_settings(self):
        provider = ElevenLabsProvider(api_key="test-key")
        fake_audio = b"fake-mp3"

        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = iter([fake_audio])
        provider._client = mock_client

        # Mock the VoiceSettings class since elevenlabs may not be installed
        mock_voice_settings = MagicMock()
        with patch("app.audio.providers.elevenlabs.ElevenLabsProvider._generate_sync") as mock_sync:
            # Simulate what _generate_sync returns on success
            mock_sync.return_value = fake_audio
            settings = {"stability": 0.7, "similarity_boost": 0.9, "style": 0.3}
            result = await provider.generate_tts("Test", "voice-1", settings)
            assert result is not None
            mock_sync.assert_called_once_with("Test", "voice-1", settings)

    @pytest.mark.asyncio
    async def test_generate_tts_handles_exception(self):
        provider = ElevenLabsProvider(api_key="test-key")

        mock_client = MagicMock()
        mock_client.text_to_speech.convert.side_effect = RuntimeError("API down")
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "voice-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_sound_effect_calls_sdk(self):
        provider = ElevenLabsProvider(api_key="test-key")
        fake_audio = b"fake-sfx-data"

        mock_client = MagicMock()
        mock_client.text_to_sound_effects.convert.return_value = iter([fake_audio])
        provider._client = mock_client

        result = await provider.generate_sound_effect("explosion", 3.0)

        assert result == fake_audio
        mock_client.text_to_sound_effects.convert.assert_called_once_with(
            text="explosion",
            duration_seconds=3.0,
        )

    @pytest.mark.asyncio
    async def test_generate_sound_effect_no_key(self):
        provider = ElevenLabsProvider(api_key=None)
        provider._api_key = None
        result = await provider.generate_sound_effect("explosion", 3.0)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_voices_no_key(self):
        provider = ElevenLabsProvider(api_key=None)
        provider._api_key = None
        result = await provider.list_voices()
        assert result == []
