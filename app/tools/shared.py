"""Lead lookups that several agents use."""

import json

from app import db
from app.tools import stub_data


async def get_lead(lead_id: int) -> dict:
    """Get everything known about one lead: company, research, contact, stage, and its draft if any."""
    lead = db.get_lead(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    lead = {k: v for k, v in lead.items() if k != "research_json"} | {"research": json.loads(lead["research_json"] or "{}")}
    return {**lead, "draft": stub_data.DRAFTS.get(lead_id)}


async def list_leads() -> list[dict]:
    """List all leads with their id, company, stage and tier (null until Researcher has checked it).

    Use it to find which lead someone means.
    """
    return [{"lead_id": l["id"], "company": l["company"], "stage": l["stage"], "tier": l["tier"]} for l in db.list_leads()]
