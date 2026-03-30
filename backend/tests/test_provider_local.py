"""Tests for the local Voxtral provider."""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.audio.providers.local import LocalVoiceProvider


class TestLocalProvider:
    def test_name(self):
        provider = LocalVoiceProvider()
        assert provider.name == "local"

    def test_supports_cloning(self):
        provider = LocalVoiceProvider()
        assert provider.supports_cloning() is True

    def test_no_sound_effects(self):
        provider = LocalVoiceProvider()
        assert provider.supports_sound_effects() is False

    def test_default_url(self):
        with patch.dict("os.environ", {}, clear=True):
            provider = LocalVoiceProvider()
            assert provider._base_url == "http://localhost:8080"

    def test_custom_url_from_env(self):
        with patch.dict("os.environ", {"LOCAL_TTS_URL": "http://myserver:9090"}):
            provider = LocalVoiceProvider()
            assert provider._base_url == "http://myserver:9090"

    def test_custom_url_from_arg(self):
        provider = LocalVoiceProvider(base_url="http://custom:1234")
        assert provider._base_url == "http://custom:1234"

    @pytest.mark.asyncio
    async def test_generate_tts_success(self):
        provider = LocalVoiceProvider()
        fake_audio = b"local-audio-data"

        mock_response = MagicMock()
        mock_response.content = fake_audio
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "local-voice-1")

        assert result is not None
        assert base64.b64decode(result) == fake_audio
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "/v1/audio/speech"
        payload = call_args[1]["json"]
        assert payload["input"] == "Hello"
        assert payload["voice"] == "local-voice-1"
        assert payload["model"] == "voxtral-mini"

    @pytest.mark.asyncio
    async def test_generate_tts_connection_error(self):
        provider = LocalVoiceProvider()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_tts_other_error(self):
        provider = LocalVoiceProvider()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("Server error"))
        provider._client = mock_client

        result = await provider.generate_tts("Hello", "v1")
        assert result is None

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        provider = LocalVoiceProvider()

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        provider._client = mock_client

        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        provider = LocalVoiceProvider()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        provider._client = mock_client

        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_list_voices_connection_error(self):
        provider = LocalVoiceProvider()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        provider._client = mock_client

        result = await provider.list_voices()
        assert result == []
