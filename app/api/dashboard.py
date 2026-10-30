"""API routes for the Dashboard: what the process cost in AI tokens, where each lead stands, and the revenue it brought in.

AI cost is read from Flexprice when FLEXPRICE_API_KEY is set (`source: "flexprice"`), else from SQLite.

A lead becomes a client through a deal the founder records: 'potential' while they're talking, then
'confirmed' (with the agreed value, which counts as revenue) or 'lost'.
"""

from __future__ import annotations

import json
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app import db
from app.connectors import flexprice

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class DealIn(BaseModel):
    status: Literal["potential", "confirmed", "lost"]
    value_usd: float = Field(0, ge=0)
    note: str | None = None


def _cost(c) -> dict:
    """AI cost from the local usage table: what Flexprice will have once everything is synced."""
    rows = c.execute("SELECT agent, props_json, cost_usd, created_at FROM usage WHERE event_name = 'llm.call'").fetchall()
    by_agent: dict[str, dict] = {}
    daily: dict[str, float] = {}
    tokens = 0
    for r in rows:
        props = json.loads(r["props_json"] or "{}")
        t = props.get("input_tokens", 0) + props.get("output_tokens", 0)
        tokens += t
        a = by_agent.setdefault(r["agent"] or "tool", {"agent": r["agent"] or "tool", "calls": 0, "tokens": 0, "cost_usd": 0.0})
        a["calls"] += 1
        a["tokens"] += t
        a["cost_usd"] += r["cost_usd"]
        daily[r["created_at"][:10]] = daily.get(r["created_at"][:10], 0) + r["cost_usd"]
    return {
        "total_usd": sum(r["cost_usd"] for r in rows),
        "calls": len(rows),
        "tokens": tokens,
        "by_agent": sorted(by_agent.values(), key=lambda a: -a["cost_usd"]),
        "daily": [{"day": d, "cost_usd": v} for d, v in sorted(daily.items())],
    }


def _sync(c) -> dict:
    pending = c.execute("SELECT COUNT(*) FROM usage WHERE synced = 0").fetchone()[0]
    pending += c.execute("SELECT COUNT(*) FROM deals WHERE status = 'confirmed' AND synced_at IS NULL").fetchone()[0]
    sent = c.execute("SELECT COUNT(*) FROM usage WHERE synced = 1").fetchone()[0]
    return {"connected": flexprice.enabled(), "pending_events": pending, "sent_events": sent, "error": None}


def _reply_rates(c) -> dict:
    """Reply rate (replied or meeting / contacted) by industry and by the email angle sent."""
    rows = c.execute(
        "SELECT l.industry, o.outcome, "
        "  (SELECT angle FROM drafts d WHERE d.lead_id = l.id AND d.channel = 'email' AND d.status IN ('sent', 'approved') "
        "   ORDER BY d.status = 'sent' DESC LIMIT 1) AS angle "
        "FROM leads l JOIN outcomes o ON o.lead_id = l.id WHERE l.stage != 'skipped'"
    ).fetchall()

    def group(key: str) -> list[dict]:
        out: dict[str, dict] = {}
        for r in rows:
            if not r[key]:
                continue
            g = out.setdefault(r[key], {"key": r[key], "sent": 0, "replied": 0})
            g["sent"] += 1
            g["replied"] += r["outcome"] in ("replied", "meeting")
        return sorted(out.values(), key=lambda g: -g["replied"] / g["sent"])

    return {"by_industry": group("industry"), "by_angle": group("angle")}


@router.get("")
async def dashboard() -> dict:
    with db.connect() as c:
        cost = _cost(c)
        sync = _sync(c)
        reply_rates = _reply_rates(c)
        leads = c.execute("SELECT id, stage FROM leads WHERE stage != 'skipped'").fetchall()
        outcomes = {r["lead_id"]: r["outcome"] for r in c.execute("SELECT lead_id, outcome FROM outcomes ORDER BY logged_at")}
        deals = [dict(r) for r in c.execute(
            "SELECT d.*, l.company, l.person_name, l.industry FROM deals d JOIN leads l ON l.id = d.lead_id ORDER BY d.updated_at DESC"
        )]

    by_status = {s: [d for d in deals if d["status"] == s] for s in ("potential", "confirmed", "lost")}
    revenue = sum(d["value_usd"] for d in by_status["confirmed"])

    # AI cost comes from Flexprice when it's connected, the local usage table otherwise. Revenue is always the
    # deals table: Flexprice keeps every deal.confirmed event ever sent, so a deal edited or re-entered would count twice.
    source = "local"
    if flexprice.enabled():
        try:
            fp = await flexprice.report([a["agent"] for a in cost["by_agent"]])
            cost = {
                **cost,
                "total_usd": fp["cost_usd"],
                "calls": int(fp["calls"]),
                "tokens": int(fp["tokens"]),
                "daily": fp["daily"] or cost["daily"],
                "by_agent": sorted(({**a, "cost_usd": fp["by_agent"].get(a["agent"], 0)} for a in cost["by_agent"]), key=lambda a: -a["cost_usd"]),
            }
            source = "flexprice"
        except httpx.HTTPError as e:
            sync["error"] = str(e)

    confirmed = len(by_status["confirmed"])
    clients = {
        "leads": len(leads),
        "contacted": sum(1 for l in leads if l["stage"] == "sent" or l["id"] in outcomes),
        "replied": sum(1 for o in outcomes.values() if o in ("replied", "meeting")),
        "meetings": sum(1 for o in outcomes.values() if o == "meeting"),
        "potential": len(by_status["potential"]),
        "confirmed": confirmed,
        "lost": len(by_status["lost"]),
    }
    return {
        "source": source,
        "sync": sync,
        "cost": {
            **cost,
            "per_lead_usd": cost["total_usd"] / clients["leads"] if clients["leads"] else None,
            "per_reply_usd": cost["total_usd"] / clients["replied"] if clients["replied"] else None,
            "per_client_usd": cost["total_usd"] / confirmed if confirmed else None,
        },
        "clients": clients,
        "revenue": {
            "confirmed_usd": revenue,
            "pipeline_usd": sum(d["value_usd"] for d in by_status["potential"]),
            "avg_deal_usd": revenue / confirmed if confirmed else None,
            "net_usd": revenue - cost["total_usd"],
            "roi": revenue / cost["total_usd"] if cost["total_usd"] else None,
        },
        "reply_rates": reply_rates,
        "deals": deals,
    }


@router.put("/deals/{lead_id}")
def save_deal(lead_id: int, deal: DealIn) -> dict:
    if db.get_lead(lead_id) is None:
        raise HTTPException(404, "No such lead")
    with db.connect() as c:
        c.execute(
            "INSERT INTO deals (lead_id, status, value_usd, note) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(lead_id) DO UPDATE SET status = excluded.status, value_usd = excluded.value_usd, "
            "note = excluded.note, synced_at = NULL, updated_at = CURRENT_TIMESTAMP",
            (lead_id, deal.status, deal.value_usd, deal.note),
        )
    return {"saved": True}


@router.delete("/deals/{lead_id}")
def delete_deal(lead_id: int) -> dict:
    with db.connect() as c:
        c.execute("DELETE FROM deals WHERE lead_id = ?", (lead_id,))
    return {"deleted": True}
