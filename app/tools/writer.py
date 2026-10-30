"""Writer's tools: drafting outreach and carrying out the founder's decisions on drafts."""

from typing import Annotated

from pydantic import Field

from app import db
from app.tools import stub_data


async def draft_outreach(
    lead_id: int,
    feedback: Annotated[str | None, Field(description="The founder's feedback when rewriting a draft")] = None,
) -> dict:
    """Write the cited why-now story and the outreach email for a researched lead.

    The draft goes to the approval queue in the First100 web app, where the founder reviews it.
    Pass `feedback` to rewrite an existing draft.
    """
    if lead_id not in stub_data.LEADS and (real := db.get_lead(lead_id)):
        # TODO: write from the database lead once drafting is built
        return {"error": f"Writing isn't connected yet, so there's no draft for {real['company']} (lead {lead_id})."}
    lead = stub_data.LEADS.get(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    if not lead.get("contact"):
        return {"error": f"{lead['company']} has no contact yet; it needs research first."}
    # TODO: cited story + A/B drafts (Ollama) with word-count, cliché and citation checks
    first_name = lead["contact"]["name"].split()[0]
    draft = {
        "to": lead["contact"],
        "angle": "signal",
        "subject": f"Quick idea for {lead['company']}",
        "preview": f"Hi {first_name}, saw {lead['company']} just {lead['signal']}…",
        "status": "pending",
        "where": "approval queue in First100",
    }
    stub_data.DRAFTS[lead_id] = draft
    lead["stage"] = "drafted"
    return {"lead_id": lead_id, "company": lead["company"], **draft}


async def approve_draft(lead_id: int) -> dict:
    """Approve a lead's draft and send it (sending is simulated)."""
    draft = stub_data.DRAFTS.get(lead_id)
    if draft is None:
        return {"error": f"No draft for lead {lead_id}."}
    # TODO: same route as the web app's Approve button
    draft["status"] = "sent"
    stub_data.LEADS[lead_id]["stage"] = "sent"
    return {"lead_id": lead_id, "status": "sent", "to": draft["to"], "simulated": True}


async def reject_draft(lead_id: int) -> dict:
    """Throw away a lead's draft."""
    draft = stub_data.DRAFTS.get(lead_id)
    if draft is None:
        return {"error": f"No draft for lead {lead_id}."}
    draft["status"] = "rejected"
    return {"lead_id": lead_id, "status": "rejected"}
