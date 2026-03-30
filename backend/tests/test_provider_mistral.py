"""Tests for the Mistral Voxtral provider."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.audio.providers.mistral import MistralVoiceProvider


class TestMistralProvider:
    def test_name(self):
        provider = MistralVoiceProvider(api_key="test-key")
        assert provider.name == "mistral"

    def test_supports_cloning(self):
        provider = MistralVoiceProvider(api_key="test-key")
        assert provider.supports_cloning() is True

    def test_no_sound_effects(self):
        provider = MistralVoiceProvider(api_key="test-key")
        assert provider.supports_sound_effects() is False

    def test_no_api_key_returns_none_for_client(self):
        provider = MistralVoiceProvider(api_key=None)
        with patch.dict("os.environ", {}, clear=True):
            provider._api_key = None
            client = provider._get_client()
            assert client is None

    @pytest.mark.asyncio
    async def test_generate_tts_no_api_key(self):
        provider = MistralVoiceProvider(api_key=None)
        provider._api_key = None
        result = await provider.generate_tts("hello", "voice-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_tts_success(self):
        provider = MistralVoiceProvider(api_key="test-key")
        fake_audio = b"fake-mp3-data"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = fake_audio
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_tts("Hello world", "mistral-voice-1")

        assert result is not None
        assert base64.b64decode(result) == fake_audio
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["input"] == "Hello world"
        assert payload["voice"] == "mistral-voice-1"
        assert payload["response_format"] == "mp3"

    @pytest.mark.asyncio
    async def test_generate_tts_with_speed(self):
        provider = MistralVoiceProvider(api_key="test-key")
        fake_audio = b"fast-audio"

        mock_response = MagicMock()
        mock_response.content = fake_audio
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "v1", {"speed": 1.5})

        payload = mock_client.post.call_args[1]["json"]
        assert payload["speed"] == 1.5

    @pytest.mark.asyncio
    async def test_generate_tts_handles_error(self):
        provider = MistralVoiceProvider(api_key="test-key")

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Network error"))
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_voices_success(self):
        provider = MistralVoiceProvider(api_key="test-key")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "voices": [
                {"id": "v1", "name": "Voice One", "languages": ["en"], "type": "standard"},
                {"id": "v2", "name": "Voice Two", "languages": ["fr"], "type": "cloned"},
            ]
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        voices = await provider.list_voices()
        assert len(voices) == 2
        assert voices[0].voice_id == "v1"
        assert voices[0].provider == "mistral"
        assert voices[0].cloned is False
        assert voices[1].cloned is True
