"""Tests for the multi-provider voice registry."""

import json

import pytest

from app.audio.registry import (
    _resolve_entry,
    get_voice_id,
    get_voice_settings,
    load_registry,
)


class TestLoadRegistry:
    def test_loads_existing_registry(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert "narrator" in registry
        assert "npcs" in registry
        assert registry["narrator"]["voice_id"] == "narrator-voice-001"

    def test_missing_file_returns_defaults(self, tmp_path):
        registry = load_registry(tmp_path / "nonexistent")
        assert registry == {"narrator": None, "npcs": {}, "ambience": {}}


class TestResolveEntry:
    def test_none_entry(self):
        assert _resolve_entry(None, "elevenlabs") is None

    def test_legacy_flat_format_matches_elevenlabs(self):
        entry = {"voice_id": "abc", "settings": {"stability": 0.5}}
        result = _resolve_entry(entry, "elevenlabs")
        assert result == entry

    def test_legacy_flat_format_returns_none_for_other_provider(self):
        entry = {"voice_id": "abc", "settings": {"stability": 0.5}}
        assert _resolve_entry(entry, "mistral") is None
        assert _resolve_entry(entry, "local") is None

    def test_multi_provider_format(self):
        entry = {
            "elevenlabs": {"voice_id": "el-001", "settings": {"stability": 0.5}},
            "mistral": {"voice_id": "mi-001"},
        }
        assert _resolve_entry(entry, "elevenlabs")["voice_id"] == "el-001"
        assert _resolve_entry(entry, "mistral")["voice_id"] == "mi-001"
        assert _resolve_entry(entry, "local") is None

    def test_entry_with_no_voice_id_and_no_providers(self):
        # An entry that has neither provider keys nor voice_id
        entry = {"voice_name": "something", "style": "dramatic"}
        assert _resolve_entry(entry, "elevenlabs") is None


class TestGetVoiceId:
    def test_narrator_legacy_format(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert get_voice_id(registry, "narrator") == "narrator-voice-001"
        assert get_voice_id(registry, "narrator", "elevenlabs") == "narrator-voice-001"

    def test_npc_legacy_format(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert get_voice_id(registry, "Gandalf") == "gandalf-voice-001"

    def test_legacy_format_returns_none_for_non_elevenlabs(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert get_voice_id(registry, "narrator", "mistral") is None
        assert get_voice_id(registry, "Gandalf", "local") is None

    def test_narrator_multi_provider(self, multi_provider_campaign):
        registry = load_registry(multi_provider_campaign)
        assert get_voice_id(registry, "narrator", "elevenlabs") == "el-narrator-001"
        assert get_voice_id(registry, "narrator", "mistral") == "mi-narrator-001"
        assert get_voice_id(registry, "narrator", "local") == "local-narrator-001"

    def test_npc_multi_provider(self, multi_provider_campaign):
        registry = load_registry(multi_provider_campaign)
        assert get_voice_id(registry, "Gandalf", "elevenlabs") == "el-gandalf-001"
        assert get_voice_id(registry, "Gandalf", "mistral") == "mi-gandalf-001"
        # Gandalf has no local mapping
        assert get_voice_id(registry, "Gandalf", "local") is None

    def test_unknown_speaker(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert get_voice_id(registry, "NonexistentNPC") is None


class TestGetVoiceSettings:
    def test_narrator_legacy_format(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        settings = get_voice_settings(registry, "narrator")
        assert settings["stability"] == 0.5
        assert settings["similarity_boost"] == 0.75

    def test_npc_legacy_format(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        settings = get_voice_settings(registry, "Gandalf")
        assert settings["stability"] == 0.6

    def test_settings_multi_provider(self, multi_provider_campaign):
        registry = load_registry(multi_provider_campaign)
        el_settings = get_voice_settings(registry, "narrator", "elevenlabs")
        assert el_settings["stability"] == 0.5
        mi_settings = get_voice_settings(registry, "narrator", "mistral")
        assert mi_settings["speed"] == 1.0

    def test_no_settings_returns_none(self, multi_provider_campaign):
        registry = load_registry(multi_provider_campaign)
        # local narrator has no settings key
        settings = get_voice_settings(registry, "narrator", "local")
        assert settings is None

    def test_non_elevenlabs_on_legacy_returns_none(self, tmp_campaign):
        registry = load_registry(tmp_campaign)
        assert get_voice_settings(registry, "narrator", "mistral") is None
