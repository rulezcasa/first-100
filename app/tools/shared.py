"""Lead lookups that several agents use."""

import json

from app import db


async def get_lead(lead_id: int) -> dict:
    """Get everything known about one lead: company, research, contact, stage, story and its drafts."""
    lead = db.get_lead(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    lead = {k: v for k, v in lead.items() if k != "research_json"} | {"research": json.loads(lead["research_json"] or "{}")}
    lead["story"] = json.loads(lead.pop("story_json") or "[]")
    return {**lead, "drafts": [{k: d[k] for k in ("id", "channel", "variant", "angle", "subject", "status")}
                               for d in db.list_drafts(lead_id)]}


async def list_leads() -> list[dict]:
    """List all leads with their id, company, stage and tier (null until Researcher has checked it).

    Use it to find which lead someone means.
    """
    return [{"lead_id": l["id"], "company": l["company"], "stage": l["stage"], "tier": l["tier"]} for l in db.list_leads()]
