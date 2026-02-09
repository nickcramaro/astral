"""Voice registry — maps narrator, NPCs, and ambience to ElevenLabs voices."""

import json
from pathlib import Path


def load_registry(campaign_dir: Path) -> dict:
    """Load voice-registry.json for a campaign."""
    registry_path = campaign_dir / "voice-registry.json"
    if registry_path.exists():
        return json.loads(registry_path.read_text())
    return {"narrator": None, "npcs": {}, "ambience": {}}


def get_voice_id(registry: dict, speaker: str) -> str | None:
    """Look up the ElevenLabs voice ID for a speaker."""
    if speaker == "narrator":
        return registry.get("narrator", {}).get("voice_id")
    return registry.get("npcs", {}).get(speaker, {}).get("voice_id")
