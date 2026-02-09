"""Campaign management routes — list, detail, import."""

from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.get("/")
async def list_campaigns():
    """List all available campaigns."""
    # TODO: Scan data/campaigns/ and return metadata
    return []


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get campaign detail including character info."""
    # TODO: Load campaign overview + character JSON
    return {"id": campaign_id}


@router.post("/import")
async def import_campaign(file: UploadFile):
    """Upload a PDF and kick off the import pipeline."""
    # TODO: Save PDF, run extraction pipeline, stream progress
    return {"status": "accepted", "filename": file.filename}
