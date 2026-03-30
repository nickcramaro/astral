"""Tests for the provider factory and base class."""

import os
from unittest.mock import patch

import pytest

from app.audio.providers import _providers, get_sfx_provider, get_voice_provider
from app.audio.providers.base import VoiceInfo, VoiceProvider
from app.audio.providers.elevenlabs import ElevenLabsProvider
from app.audio.providers.local import LocalVoiceProvider
from app.audio.providers.mistral import MistralVoiceProvider


@pytest.fixture(autouse=True)
def clear_provider_cache():
    """Clear the singleton cache between tests."""
    _providers.clear()
    yield
    _providers.clear()


class TestProviderFactory:
    def test_default_provider_is_elevenlabs(self):
        with patch.dict(os.environ, {}, clear=True):
            # VOICE_PROVIDER unset → defaults to elevenlabs
            provider = get_voice_provider()
            assert isinstance(provider, ElevenLabsProvider)
            assert provider.name == "elevenlabs"

    def test_env_selects_mistral(self):
        with patch.dict(os.environ, {"VOICE_PROVIDER": "mistral"}):
            provider = get_voice_provider()
            assert isinstance(provider, MistralVoiceProvider)
            assert provider.name == "mistral"

    def test_env_selects_local(self):
        with patch.dict(os.environ, {"VOICE_PROVIDER": "local"}):
            provider = get_voice_provider()
            assert isinstance(provider, LocalVoiceProvider)
            assert provider.name == "local"

    def test_explicit_name_overrides_env(self):
        with patch.dict(os.environ, {"VOICE_PROVIDER": "elevenlabs"}):
            provider = get_voice_provider("local")
            assert isinstance(provider, LocalVoiceProvider)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown voice provider"):
            get_voice_provider("nonexistent")

    def test_singleton_caching(self):
        p1 = get_voice_provider("local")
        p2 = get_voice_provider("local")
        assert p1 is p2

    def test_different_providers_are_different_instances(self):
        p1 = get_voice_provider("local")
        p2 = get_voice_provider("mistral")
        assert p1 is not p2

    def test_case_insensitive(self):
        p = get_voice_provider("ElevenLabs")
        assert isinstance(p, ElevenLabsProvider)


class TestSfxProvider:
    def test_sfx_returns_elevenlabs_when_it_supports_sfx(self):
        """ElevenLabs supports SFX, so it should be returned."""
        with patch.dict(os.environ, {"VOICE_PROVIDER": "elevenlabs"}):
            provider = get_sfx_provider()
            assert provider is not None
            assert provider.supports_sound_effects()

    def test_sfx_falls_back_to_elevenlabs_when_primary_has_no_sfx(self):
        """Mistral doesn't support SFX — should fall back to ElevenLabs if key is set."""
        with patch.dict(os.environ, {
            "VOICE_PROVIDER": "mistral",
            "ELEVENLABS_API_KEY": "test-key",
        }):
            provider = get_sfx_provider()
            assert provider is not None
            assert isinstance(provider, ElevenLabsProvider)

    def test_sfx_returns_none_when_no_sfx_support_and_no_fallback(self):
        """No ElevenLabs key, primary doesn't support SFX → None."""
        with patch.dict(os.environ, {"VOICE_PROVIDER": "local"}, clear=True):
            provider = get_sfx_provider()
            assert provider is None


class TestVoiceInfo:
    def test_voice_info_defaults(self):
        info = VoiceInfo(voice_id="v1", name="Test", provider="test")
        assert info.voice_id == "v1"
        assert info.language_codes == []
        assert info.preview_url is None
        assert info.cloned is False

    def test_voice_info_cloned(self):
        info = VoiceInfo(voice_id="v1", name="Clone", provider="test", cloned=True)
        assert info.cloned is True


class TestBaseClassDefaults:
    """Verify that the ABC default implementations return safe values."""

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            VoiceProvider()
