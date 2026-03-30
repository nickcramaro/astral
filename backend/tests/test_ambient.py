"""Tests for ambient/SFX generation with provider injection."""

import base64

import pytest

from app.audio.ambient import AUDIO_CACHE, _cache_key, get_ambient, get_sfx


class TestCacheKey:
    def test_includes_provider_name(self):
        path1 = _cache_key("ambient", "forest sounds", "elevenlabs")
        path2 = _cache_key("ambient", "forest sounds", "mistral")
        assert path1 != path2
        assert "elevenlabs" in path1.name
        assert "mistral" in path2.name

    def test_same_inputs_same_key(self):
        p1 = _cache_key("sfx", "explosion", "local")
        p2 = _cache_key("sfx", "explosion", "local")
        assert p1 == p2

    def test_different_descriptions_different_keys(self):
        p1 = _cache_key("ambient", "forest", "elevenlabs")
        p2 = _cache_key("ambient", "tavern", "elevenlabs")
        assert p1 != p2


class TestGetAmbient:
    @pytest.mark.asyncio
    async def test_returns_none_without_provider(self):
        result = await get_ambient("forest sounds", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_generates_and_caches(self, fake_sfx_provider, tmp_path, monkeypatch):
        # Point cache to tmp dir
        monkeypatch.setattr("app.audio.ambient.AUDIO_CACHE", tmp_path)

        result = await get_ambient("forest sounds", fake_sfx_provider)

        assert result is not None
        decoded = base64.b64decode(result)
        assert decoded == b"sfx:forest sounds"
        assert len(fake_sfx_provider.sfx_calls) == 1
        assert fake_sfx_provider.sfx_calls[0]["duration"] == 10.0

        # Second call should hit cache — no new SFX calls
        result2 = await get_ambient("forest sounds", fake_sfx_provider)
        assert result2 == result
        assert len(fake_sfx_provider.sfx_calls) == 1  # Still 1

    @pytest.mark.asyncio
    async def test_generation_failure_returns_none(self, fake_sfx_provider, tmp_path, monkeypatch):
        monkeypatch.setattr("app.audio.ambient.AUDIO_CACHE", tmp_path)
        fake_sfx_provider._fail_sfx = True

        result = await get_ambient("wind", fake_sfx_provider)
        assert result is None


class TestGetSfx:
    @pytest.mark.asyncio
    async def test_returns_none_without_provider(self):
        result = await get_sfx("explosion", None)
        assert result is None

    @pytest.mark.asyncio
    async def test_generates_and_caches(self, fake_sfx_provider, tmp_path, monkeypatch):
        monkeypatch.setattr("app.audio.ambient.AUDIO_CACHE", tmp_path)

        result = await get_sfx("sword clash", fake_sfx_provider)

        assert result is not None
        assert len(fake_sfx_provider.sfx_calls) == 1
        assert fake_sfx_provider.sfx_calls[0]["duration"] == 3.0

        # Cache hit
        result2 = await get_sfx("sword clash", fake_sfx_provider)
        assert result2 == result
        assert len(fake_sfx_provider.sfx_calls) == 1

    @pytest.mark.asyncio
    async def test_generation_failure_returns_none(self, fake_sfx_provider, tmp_path, monkeypatch):
        monkeypatch.setattr("app.audio.ambient.AUDIO_CACHE", tmp_path)
        fake_sfx_provider._fail_sfx = True

        result = await get_sfx("explosion", fake_sfx_provider)
        assert result is None
