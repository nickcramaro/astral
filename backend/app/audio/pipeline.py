"""Audio pipeline — coordinates parsing, TTS, and sound generation for a DM turn."""

import logging
from pathlib import Path
from typing import AsyncGenerator

from app.audio.ambient import get_ambient, get_sfx
from app.audio.providers import VoiceProvider, get_sfx_provider, get_voice_provider
from app.audio.registry import get_voice_id, get_voice_settings, load_registry
from app.orchestrator.parser import Segment, parse_segments

log = logging.getLogger(__name__)

# Which segment types are enabled for each audio mode
MODE_FILTER: dict[str, set[str]] = {
    "full": {"narrate", "npc", "ambient", "sfx"},
    "dialogue": {"npc", "ambient", "sfx"},
    "ambient": {"ambient", "sfx"},
    "off": set(),
}


class AudioPipeline:
    """Generates audio WebSocket messages from parsed DM text."""

    def __init__(
        self,
        campaign_dir: Path,
        audio_mode: str = "full",
        voice_provider: VoiceProvider | None = None,
        sfx_provider: VoiceProvider | None = None,
    ):
        self.registry = load_registry(campaign_dir)
        self.audio_mode = audio_mode
        self._voice = voice_provider or get_voice_provider()
        self._sfx = sfx_provider if sfx_provider is not None else get_sfx_provider()

    @property
    def provider_name(self) -> str:
        return self._voice.name

    def set_mode(self, mode: str) -> None:
        self.audio_mode = mode

    async def process_text(self, raw_text: str) -> AsyncGenerator[dict, None]:
        """Parse raw DM text and generate audio messages for each segment."""
        for segment in parse_segments(raw_text):
            async for msg in self.process_segment(segment):
                yield msg

    async def process_segment(
        self, segment: Segment
    ) -> AsyncGenerator[dict, None]:
        """Generate audio for a single segment if its type is allowed."""
        allowed = MODE_FILTER.get(self.audio_mode, set())
        if segment.type not in allowed:
            return

        provider_name = self._voice.name

        if segment.type == "narrate":
            voice_id = get_voice_id(self.registry, "narrator", provider_name)
            if not voice_id:
                return
            settings = get_voice_settings(self.registry, "narrator", provider_name)
            data = await self._voice.generate_tts(segment.content, voice_id, settings)
            if data:
                yield {"type": "audio", "channel": "voice", "speaker": "narrator", "data": data}

        elif segment.type == "npc":
            npc_name = segment.meta
            voice_id = get_voice_id(self.registry, npc_name, provider_name)
            if not voice_id:
                log.warning("No voice registered for NPC: %s (provider: %s)", npc_name, provider_name)
                return
            settings = get_voice_settings(self.registry, npc_name, provider_name)
            data = await self._voice.generate_tts(segment.content, voice_id, settings)
            if data:
                yield {"type": "audio", "channel": "voice", "speaker": npc_name, "data": data}

        elif segment.type == "ambient":
            data = await get_ambient(segment.meta, self._sfx)
            if data:
                yield {"type": "audio", "channel": "ambient", "data": data}

        elif segment.type == "sfx":
            data = await get_sfx(segment.meta, self._sfx)
            if data:
                yield {"type": "audio", "channel": "sfx", "data": data}
