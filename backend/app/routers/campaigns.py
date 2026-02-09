"""Campaign management routes — list, detail, import."""

import json
from pathlib import Path

from fastapi import APIRouter, UploadFile

router = APIRouter()

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CAMPAIGNS_DIR = DATA_DIR / "campaigns"


@router.get("/")
async def list_campaigns():
    """List all available campaigns."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    campaigns = []

    for campaign_dir in sorted(CAMPAIGNS_DIR.iterdir()):
        if not campaign_dir.is_dir():
            continue

        campaign = {"id": campaign_dir.name, "name": campaign_dir.name}

        # Read overview
        overview_path = campaign_dir / "campaign-overview.json"
        if overview_path.exists():
            try:
                overview = json.loads(overview_path.read_text())
                campaign["name"] = overview.get("campaign_name", campaign_dir.name)
                campaign["sessionCount"] = overview.get("session_count", 0)
            except (json.JSONDecodeError, IOError):
                pass

        # Read character
        char_path = campaign_dir / "character.json"
        campaign["hasCharacter"] = char_path.exists()
        if char_path.exists():
            try:
                char = json.loads(char_path.read_text())
                campaign["character"] = {
                    "name": char.get("name", "Unknown"),
                    "race": char.get("race", "?"),
                    "class": char.get("class", "?"),
                    "level": char.get("level", 1),
                }
            except (json.JSONDecodeError, IOError):
                pass

        # Count entities
        counts = {}
        for entity_file in ["npcs.json", "locations.json", "plots.json"]:
            entity_path = campaign_dir / entity_file
            if entity_path.exists():
                try:
                    data = json.loads(entity_path.read_text())
                    key = entity_file.replace(".json", "")
                    counts[key] = len(data) if isinstance(data, (dict, list)) else 0
                except (json.JSONDecodeError, IOError):
                    pass
        if counts:
            campaign["entityCounts"] = counts

        campaigns.append(campaign)

    return campaigns


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get campaign detail including character info."""
    campaign_dir = CAMPAIGNS_DIR / campaign_id
    if not campaign_dir.is_dir():
        return {"error": "Campaign not found"}

    result = {"id": campaign_id}

    # Load all JSON files
    for filename in ["campaign-overview.json", "character.json", "npcs.json", "locations.json", "plots.json"]:
        filepath = campaign_dir / filename
        if filepath.exists():
            try:
                key = filename.replace(".json", "").replace("-", "_")
                result[key] = json.loads(filepath.read_text())
            except (json.JSONDecodeError, IOError):
                pass

    return result


@router.post("/import")
async def import_campaign(file: UploadFile):
    """Upload a PDF and kick off the import pipeline."""
    # TODO: M2 — save PDF, run extraction pipeline, stream progress
    return {"status": "accepted", "filename": file.filename}
