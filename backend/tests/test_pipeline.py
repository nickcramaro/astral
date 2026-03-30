"""Tests for the audio pipeline with provider injection."""

import pytest

from app.audio.pipeline import AudioPipeline, MODE_FILTER
from app.orchestrator.parser import Segment


@pytest.fixture(autouse=True)
def isolate_audio_cache(tmp_path, monkeypatch):
    """Redirect audio cache to tmp dir so tests don't pollute real cache."""
    monkeypatch.setattr("app.audio.ambient.AUDIO_CACHE", tmp_path / "audio-cache")


class TestAudioPipeline:
    @pytest.mark.asyncio
    async def test_narrate_segment_uses_provider(self, tmp_campaign, fake_provider):
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
        )
        # Override provider name to match legacy registry (elevenlabs)
        fake_provider._name = "elevenlabs"

        segment = Segment(type="narrate", content="The cave looms ahead.", meta="")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["type"] == "audio"
        assert messages[0]["channel"] == "voice"
        assert messages[0]["speaker"] == "narrator"
        assert len(fake_provider.tts_calls) == 1
        assert fake_provider.tts_calls[0]["voice_id"] == "narrator-voice-001"
        assert fake_provider.tts_calls[0]["text"] == "The cave looms ahead."

    @pytest.mark.asyncio
    async def test_npc_segment_uses_provider(self, tmp_campaign, fake_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
        )

        segment = Segment(type="npc", content="You shall not pass!", meta="Gandalf")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["speaker"] == "Gandalf"
        assert fake_provider.tts_calls[0]["voice_id"] == "gandalf-voice-001"

    @pytest.mark.asyncio
    async def test_npc_no_voice_yields_nothing(self, tmp_campaign, fake_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
        )

        segment = Segment(type="npc", content="Hello!", meta="UnknownNPC")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 0
        assert len(fake_provider.tts_calls) == 0

    @pytest.mark.asyncio
    async def test_ambient_segment_uses_sfx_provider(self, tmp_campaign, fake_provider, fake_sfx_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=fake_sfx_provider,
        )

        segment = Segment(type="ambient", content="", meta="forest sounds")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["channel"] == "ambient"
        assert len(fake_sfx_provider.sfx_calls) == 1
        assert fake_sfx_provider.sfx_calls[0]["duration"] == 10.0

    @pytest.mark.asyncio
    async def test_sfx_segment_uses_sfx_provider(self, tmp_campaign, fake_provider, fake_sfx_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=fake_sfx_provider,
        )

        segment = Segment(type="sfx", content="", meta="sword clash")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 1
        assert messages[0]["channel"] == "sfx"
        assert fake_sfx_provider.sfx_calls[0]["duration"] == 3.0

    @pytest.mark.asyncio
    async def test_ambient_no_sfx_provider_yields_nothing(self, tmp_campaign, fake_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
        )

        segment = Segment(type="ambient", content="", meta="wind howling")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 0

    @pytest.mark.asyncio
    async def test_mode_filtering(self, tmp_campaign, fake_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
            audio_mode="dialogue",
        )

        # Narrate should be filtered out in dialogue mode
        segment = Segment(type="narrate", content="Scene text", meta="")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 0
        assert len(fake_provider.tts_calls) == 0

    @pytest.mark.asyncio
    async def test_off_mode_blocks_everything(self, tmp_campaign, fake_provider, fake_sfx_provider):
        fake_provider._name = "elevenlabs"
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=fake_sfx_provider,
            audio_mode="off",
        )

        for seg_type in ["narrate", "npc", "ambient", "sfx"]:
            segment = Segment(type=seg_type, content="Test", meta="Gandalf" if seg_type == "npc" else "desc")
            async for _ in pipeline.process_segment(segment):
                pytest.fail(f"Should not yield messages in off mode for {seg_type}")

    @pytest.mark.asyncio
    async def test_tts_failure_yields_nothing(self, tmp_campaign, fake_provider):
        fake_provider._name = "elevenlabs"
        fake_provider._fail_tts = True
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
            sfx_provider=None,
        )

        segment = Segment(type="narrate", content="Some text", meta="")
        messages = []
        async for msg in pipeline.process_segment(segment):
            messages.append(msg)

        assert len(messages) == 0

    def test_provider_name_property(self, tmp_campaign, fake_provider):
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
        )
        assert pipeline.provider_name == "fake"

    def test_set_mode(self, tmp_campaign, fake_provider):
        pipeline = AudioPipeline(
            campaign_dir=tmp_campaign,
            voice_provider=fake_provider,
        )
        pipeline.set_mode("ambient")
        assert pipeline.audio_mode == "ambient"


class TestModeFilter:
    def test_full_includes_all(self):
        assert MODE_FILTER["full"] == {"narrate", "npc", "ambient", "sfx"}

    def test_dialogue_excludes_narrate(self):
        assert "narrate" not in MODE_FILTER["dialogue"]
        assert "npc" in MODE_FILTER["dialogue"]

    def test_ambient_only_ambient_and_sfx(self):
        assert MODE_FILTER["ambient"] == {"ambient", "sfx"}

    def test_off_is_empty(self):
        assert MODE_FILTER["off"] == set()
