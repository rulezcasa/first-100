"""API routes for "Who should buy this": the target profile, and Scout's groups of likely buyers."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.models import Segment
from app.tools import scout

router = APIRouter(prefix="/who", tags=["who"])

# Confidence for a group the founder picked from "Try also": Scout hasn't vouched for it.
PICKED_CONFIDENCE = 0.4


def _current() -> dict:
    """The latest profile in the shape the web app's Profile type expects."""
    version, profile, change_note = db.get_profile()
    created_at = next((p["created_at"] for p in db.profile_history() if p["version"] == version), None)
    return {"version": version, "change_note": change_note, "created_at": created_at, **profile.model_dump()}


@router.get("")
def get_who() -> dict:
    return _current()


class GenerateIn(BaseModel):
    again: bool = False  # Redo: ask for a different answer than last time


@router.post("/generate")
async def generate(body: GenerateIn) -> dict:
    """Scout works out the groups from the saved setup. Replaces any earlier suggestion."""
    try:
        result = await scout.suggest_segments(again=body.again)
    except Exception as e:  # Ollama not running, bad output twice: the founder can retry
        raise HTTPException(502, f"Scout couldn't work this out just now: {e}") from e
    if "error" in result:
        raise HTTPException(400, result["error"])
    return _current()


class AddIn(BaseModel):
    name: str


@router.post("/add")
def add_expansion(body: AddIn) -> dict:
    """Move a "Try also" group into the list of groups to search."""
    _, profile, _ = db.get_profile()
    if body.name not in profile.expansion:
        raise HTTPException(404, f"'{body.name}' isn't one of the suggestions.")
    picked = Segment(name=body.name, why="You added this from the suggestions.", confidence=PICKED_CONFIDENCE)
    db.save_profile(profile.model_copy(update={
        "segments": [*profile.segments, picked],
        "expansion": [e for e in profile.expansion if e != body.name],
    }))
    return _current()
