"""Inline marker parser — splits DM text stream into typed segments.

Markers:
    [NARRATE] text...        → Narrator voice TTS
    [NPC:name] "dialogue"    → NPC voice TTS (lookup from registry)
    [AMBIENT:description]    → Trigger/crossfade ambient loop
    [SFX:description]        → One-shot sound effect
    [ROLL:notation:label]    → Dice roll (resolved server-side)
"""

import re
from dataclasses import dataclass
from typing import Generator

MARKER_PATTERN = re.compile(
    r"\[(NARRATE|NPC:[\w\s]+|AMBIENT:[\w\s,]+|SFX:[\w\s,]+|ROLL:[^\]]+)\]"
)


@dataclass
class Segment:
    type: str       # "narrate", "npc", "ambient", "sfx", "roll"
    content: str    # Text content or description
    meta: str = ""  # NPC name, ambient desc, roll notation, etc.


def parse_segments(text: str) -> Generator[Segment, None, None]:
    """Parse a complete DM response into typed segments."""
    # TODO: Implement full marker parsing
    # For streaming: accumulate text, emit segments as markers are found
    yield Segment(type="narrate", content=text)
