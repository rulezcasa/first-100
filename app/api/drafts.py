"""API routes for the Approve tab: Writer's drafts, and the founder's decisions on them."""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db

router = APIRouter(prefix="/drafts", tags=["drafts"])


def _shape(d: dict) -> dict:
    """A drafts row -> webapp/src/types.ts Draft."""
    return {
        "id": d["id"],
        "lead_id": d["lead_id"],
        "channel": d["channel"],
        "variant": d["variant"] or "A",
        "angle": d["angle"] or "signal",
        "subject": d["subject"] or "",
        "body": d["body"],
        "followups": json.loads(d["followups_json"]) if d["followups_json"] else [],
        "status": d["status"],
    }


@router.get("")
def list_drafts() -> list[dict]:
    return [_shape(d) for d in db.list_drafts()]


class DraftPatch(BaseModel):
    status: Literal["pending", "approved", "rejected", "sent"] | None = None
    subject: str | None = None
    body: str | None = None


@router.patch("/{draft_id}")
def update_draft(draft_id: int, body: DraftPatch) -> dict:
    """Edit a draft's text, or approve, reject or mark it sent."""
    if db.get_draft(draft_id) is None:
        raise HTTPException(404, f"No draft {draft_id}.")
    if body.subject is not None or body.body is not None:
        db.edit_draft(draft_id, body.subject, body.body)
    if body.status:
        db.set_draft_status(draft_id, body.status)
    return _shape(db.get_draft(draft_id))


@router.post("/send")
def send_approved() -> dict:
    """Send every approved email. Sending is simulated: the lead moves to Sent."""
    return {"sent_to": db.send_approved()}
