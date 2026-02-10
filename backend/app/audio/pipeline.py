"""Audio pipeline — coordinates parsing, TTS, and sound generation for a DM turn."""

import logging
from pathlib import Path
from typing import AsyncGenerator

from app.audio.ambient import get_ambient, get_sfx
from app.audio.registry import get_voice_id, load_registry
from app.audio.voice import generate_tts
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

    def __init__(self, campaign_dir: Path, audio_mode: str = "full"):
        self.registry = load_registry(campaign_dir)
        self.audio_mode = audio_mode

    def set_mode(self, mode: str) -> None:
        self.audio_mode = mode

    async def process_text(self, raw_text: str) -> AsyncGenerator[dict, None]:
        """Parse raw DM text and generate audio messages for each segment."""
        allowed = MODE_FILTER.get(self.audio_mode, set())
        if not allowed:
            return

        for segment in parse_segments(raw_text):
            async for msg in self._process_segment(segment, allowed):
                yield msg

    async def _process_segment(
        self, segment: Segment, allowed: set[str]
    ) -> AsyncGenerator[dict, None]:
        """Generate audio for a single segment if its type is allowed."""
        if segment.type not in allowed:
            return

        if segment.type == "narrate":
            voice_id = get_voice_id(self.registry, "narrator")
            if not voice_id:
                return
            settings = self.registry.get("narrator", {}).get("settings")
            data = await generate_tts(segment.content, voice_id, settings)
            if data:
                yield {"type": "audio", "channel": "voice", "speaker": "narrator", "data": data}

        elif segment.type == "npc":
            npc_name = segment.meta
            voice_id = get_voice_id(self.registry, npc_name)
            if not voice_id:
                log.warning("No voice registered for NPC: %s", npc_name)
                return
            settings = self.registry.get("npcs", {}).get(npc_name, {}).get("settings")
            data = await generate_tts(segment.content, voice_id, settings)
            if data:
                yield {"type": "audio", "channel": "voice", "speaker": npc_name, "data": data}

        elif segment.type == "ambient":
            data = await get_ambient(segment.meta)
            if data:
                yield {"type": "audio", "channel": "ambient", "data": data}

        elif segment.type == "sfx":
            data = await get_sfx(segment.meta)
            if data:
                yield {"type": "audio", "channel": "sfx", "data": data}
