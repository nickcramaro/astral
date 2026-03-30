"""Voice registry — maps narrator, NPCs, and ambience to provider-specific voices.

Supports two registry formats:

Legacy (flat — treated as ElevenLabs):
    {"narrator": {"voice_id": "abc123", "settings": {...}}, ...}

Multi-provider:
    {"narrator": {"elevenlabs": {"voice_id": "abc123", ...}, "mistral": {"voice_id": "..."}, ...}, ...}

The lookup functions auto-detect which format is in use per entry.
"""

import json
from pathlib import Path

# Known provider names — used to detect multi-provider format
_PROVIDERS = {"elevenlabs", "mistral", "local"}


def load_registry(campaign_dir: Path) -> dict:
    """Load voice-registry.json for a campaign."""
    registry_path = campaign_dir / "voice-registry.json"
    if registry_path.exists():
        return json.loads(registry_path.read_text())
    return {"narrator": None, "npcs": {}, "ambience": {}}


def _resolve_entry(entry: dict | None, provider: str) -> dict | None:
    """Resolve a registry entry to the config for the given provider.

    Handles both legacy (flat) and multi-provider formats.
    """
    if entry is None:
        return None

    # Multi-provider format: top-level keys are provider names
    if any(k in _PROVIDERS for k in entry):
        return entry.get(provider)

    # Legacy flat format — has voice_id directly. Treat as ElevenLabs.
    if "voice_id" in entry:
        return entry if provider == "elevenlabs" else None

    return None


def get_voice_id(registry: dict, speaker: str, provider: str = "elevenlabs") -> str | None:
    """Look up the voice ID for a speaker and provider."""
    if speaker == "narrator":
        entry = registry.get("narrator")
    else:
        entry = registry.get("npcs", {}).get(speaker)

    resolved = _resolve_entry(entry, provider)
    if resolved is None:
        return None
    return resolved.get("voice_id")


def get_voice_settings(registry: dict, speaker: str, provider: str = "elevenlabs") -> dict | None:
    """Look up provider-specific voice settings for a speaker."""
    if speaker == "narrator":
        entry = registry.get("narrator")
    else:
        entry = registry.get("npcs", {}).get(speaker)

    resolved = _resolve_entry(entry, provider)
    if resolved is None:
        return None
    return resolved.get("settings")
