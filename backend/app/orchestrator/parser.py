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
    r"\[(NARRATE|NPC:[^\]]+|AMBIENT:[^\]]+|SFX:[^\]]+|ROLL:[^\]]+)\]"
)


@dataclass
class Segment:
    type: str       # "narrate", "npc", "ambient", "sfx", "roll"
    content: str    # Text content or description
    meta: str = ""  # NPC name, ambient desc, roll notation, etc.


def parse_segments(text: str) -> Generator[Segment, None, None]:
    """Parse a complete DM response into typed segments.

    Walks through the text finding markers. Text following NARRATE/NPC markers
    becomes the segment content. AMBIENT/SFX/ROLL markers are metadata-only
    (their description is in the marker itself).
    """
    segments: list[tuple[str, str, int, int]] = []  # (type, meta, marker_start, marker_end)

    for match in MARKER_PATTERN.finditer(text):
        marker_body = match.group(1)
        marker_start = match.start()
        marker_end = match.end()

        if ":" in marker_body:
            seg_type, meta = marker_body.split(":", 1)
            seg_type = seg_type.lower()
            meta = meta.strip()
        else:
            seg_type = marker_body.lower()
            meta = ""

        segments.append((seg_type, meta, marker_start, marker_end))

    if not segments:
        # No markers at all — treat entire text as narration
        content = text.strip()
        if content:
            yield Segment(type="narrate", content=content)
        return

    for i, (seg_type, meta, marker_start, marker_end) in enumerate(segments):
        # Content runs from end of this marker to start of next marker (or end of text)
        if i + 1 < len(segments):
            content_end = segments[i + 1][2]
        else:
            content_end = len(text)

        content = text[marker_end:content_end].strip()

        if seg_type in ("ambient", "sfx", "roll"):
            # These are metadata-only — description is in the marker
            yield Segment(type=seg_type, content="", meta=meta)
        else:
            # narrate and npc carry text content
            if content:
                yield Segment(type=seg_type, content=content, meta=meta)


def strip_markers(text: str) -> str:
    """Remove all inline markers, returning clean prose for display.

    Keeps the text readable: AMBIENT/SFX markers are removed entirely,
    NARRATE markers are stripped, NPC markers become the NPC name prefix.
    """
    # Remove AMBIENT/SFX/ROLL markers entirely (they produce no visible text)
    result = re.sub(r"\[(?:AMBIENT|SFX|ROLL):[^\]]+\]\s*", "", text)
    # Replace [NARRATE] with nothing
    result = re.sub(r"\[NARRATE\]\s*", "", result)
    # Replace [NPC:Name] with "Name: "
    result = re.sub(r"\[NPC:([^\]]+)\]\s*", r"\1: ", result)
    # Clean up any double newlines left behind
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
