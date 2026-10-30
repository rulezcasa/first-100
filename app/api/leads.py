"""API routes for the Leads tab: every lead in the database, in the web app's Lead shape."""

from __future__ import annotations

import json

from fastapi import APIRouter

from app import db

router = APIRouter(prefix="/leads", tags=["leads"])


def _shape(lead: dict) -> dict:
    """A leads row plus its evidence -> webapp/src/types.ts Lead. Researcher fills tier, score and contact; Writer the story."""
    research = json.loads(lead["research_json"] or "{}")
    return {
        "id": lead["id"],
        "company": lead["company"],
        "domain": lead["domain"] or "",
        "industry": lead["industry"] or "",
        "size": "",
        "person_name": lead["person_name"],
        "title": lead["title"],
        "email": lead["email"],
        "email_status": lead["email_status"],
        "tier": lead["tier"],
        "score": lead["score"],
        "story": json.loads(lead["story_json"]) if lead["story_json"] else [],
        "evidence": [{**e, "title": e["title"] or "", "signal_type": e["signal_type"] or "other"} for e in lead["evidence"]],
        "warm_path": lead["warm_path"],
        "warm_via": research.get("warm_via"),
        "score_note": research.get("fit_reason"),
        "profile_version": lead["profile_version"],
        "stage": lead["stage"],
        "source": lead["source"],
        "cost": {"research": 0, "contact": 0, "writing": 0},
        "updated_at": lead["updated_at"],
    }


@router.get("")
def list_leads() -> list[dict]:
    return [_shape(l) for l in db.list_leads() if l["stage"] != "skipped"]
