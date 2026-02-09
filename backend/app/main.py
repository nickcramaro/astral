"""Astral — AI game master platform."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import campaigns, session

app = FastAPI(title="Astral", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns.router, prefix="/campaigns", tags=["campaigns"])
app.include_router(session.router, tags=["session"])


@app.get("/health")
async def health():
    return {"status": "ok"}
