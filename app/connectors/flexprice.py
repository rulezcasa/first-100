"""Flexprice: metering for what the process costs and earns (PLAN.md §7).

A background task sends unsent `usage` rows (AI calls) and confirmed deals to Flexprice as events,
one customer per founder. The Dashboard then reads its numbers back with Flexprice's usage API.
Without FLEXPRICE_API_KEY nothing is sent and the Dashboard falls back to the local tables.

Events (Flexprice wants every property as a string):
  llm.call        agent, lead_id, input_tokens, output_tokens, tokens, cost_usd
  deal.confirmed  lead_id, industry, value_usd
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx

from app import config, db

log = logging.getLogger(__name__)

CUSTOMER = config.FLEXPRICE_CUSTOMER  # one founder per app
BATCH = 500


def enabled() -> bool:
    return bool(config.FLEXPRICE_API_KEY)


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=config.FLEXPRICE_API_URL, headers={"x-api-key": config.FLEXPRICE_API_KEY}, timeout=30)


def _ts(sqlite_time: str) -> str:
    return sqlite_time.replace(" ", "T") + "Z"  # CURRENT_TIMESTAMP is UTC


async def _ensure_customer(http: httpx.AsyncClient) -> None:
    founder = db.get_founder()
    r = await http.post("/customers", json={"external_id": CUSTOMER, "name": founder.name or "Founder"})
    if r.status_code >= 400 and r.status_code != 409 and "already" not in r.text.lower():
        log.warning("Flexprice customer not created (%s): %s", r.status_code, r.text[:200])


async def sync_once(http: httpx.AsyncClient) -> int:
    """Send everything not yet sent; returns how many events went out."""
    with db.connect() as c:
        rows = c.execute("SELECT * FROM usage WHERE synced = 0 ORDER BY id LIMIT ?", (BATCH,)).fetchall()
        deals = c.execute(
            "SELECT d.*, l.industry FROM deals d JOIN leads l ON l.id = d.lead_id WHERE d.status = 'confirmed' AND d.synced_at IS NULL"
        ).fetchall()

    events = []
    for r in rows:
        props = json.loads(r["props_json"] or "{}")
        tin, tout = props.get("input_tokens", 0), props.get("output_tokens", 0)
        events.append({
            # SQLite reuses the ids of deleted rows, so the time keeps a new row from passing as an old event.
            "event_id": f"usage-{r['id']}-{r['created_at']}", "event_name": r["event_name"], "external_customer_id": CUSTOMER,
            "timestamp": _ts(r["created_at"]), "source": "first100",
            "properties": {"agent": r["agent"] or "tool", "lead_id": str(r["lead_id"] or ""), "input_tokens": str(tin),
                           "output_tokens": str(tout), "tokens": str(tin + tout), "cost_usd": f"{r['cost_usd']:.8f}"},
        })
    for d in deals:
        # A deal re-confirmed after an edit is a new event, so its id carries the update time.
        events.append({
            "event_id": f"deal-{d['lead_id']}-{d['updated_at']}", "event_name": "deal.confirmed", "external_customer_id": CUSTOMER,
            "timestamp": _ts(d["updated_at"]), "source": "first100",
            "properties": {"lead_id": str(d["lead_id"]), "industry": d["industry"] or "other", "value_usd": f"{d['value_usd']:.2f}"},
        })
    if not events:
        return 0

    r = await http.post("/events/bulk", json={"events": events})
    r.raise_for_status()
    with db.connect() as c:
        c.executemany("UPDATE usage SET synced = 1 WHERE id = ?", [(r["id"],) for r in rows])
        c.executemany("UPDATE deals SET synced_at = CURRENT_TIMESTAMP WHERE lead_id = ?", [(d["lead_id"],) for d in deals])
    return len(events)


async def run(every: float = 5) -> None:
    """Background task started by main.py."""
    async with _client() as http:
        await _ensure_customer(http)
        while True:
            try:
                if n := await sync_once(http):
                    log.info("Sent %d events to Flexprice", n)
            except httpx.HTTPError as e:
                log.warning("Flexprice sync failed, will retry: %s", e)
            await asyncio.sleep(every)


# --- reading usage back ---------------------------------------------------

async def _usage(http: httpx.AsyncClient, event_name: str, aggregation: str, prop: str | None = None,
                 filters: dict | None = None, window: str | None = None, days: int = 30) -> dict:
    end = datetime.now(timezone.utc)
    body = {"event_name": event_name, "aggregation_type": aggregation, "external_customer_id": CUSTOMER,
            "start_time": (end - timedelta(days=days)).isoformat(), "end_time": end.isoformat()}
    if prop:
        body["property_name"] = prop
    if filters:
        body["filters"] = filters
    if window:
        body["window_size"] = window
    r = await http.post("/events/usage", json=body)
    r.raise_for_status()
    return r.json()


async def report(agents: list[str]) -> dict:
    """AI cost, tokens and calls as Flexprice has metered them: totals, per day and per agent.
    (deal.confirmed events are sent for the record but not read back; see api/dashboard.py.)"""
    async with _client() as http:
        cost, tokens, calls, daily = await asyncio.gather(
            _usage(http, "llm.call", "SUM", "cost_usd"),
            _usage(http, "llm.call", "SUM", "tokens"),
            _usage(http, "llm.call", "COUNT"),
            _usage(http, "llm.call", "SUM", "cost_usd", window="DAY"),
        )
        per_agent = await asyncio.gather(*[
            _usage(http, "llm.call", "SUM", "cost_usd", filters={"agent": [a]}) for a in agents
        ])
    return {
        "cost_usd": cost.get("value") or 0,
        "tokens": tokens.get("value") or 0,
        "calls": calls.get("value") or 0,
        "daily": [{"day": (r.get("window_size") or "")[:10], "cost_usd": r.get("value") or 0} for r in daily.get("results") or []],
        "by_agent": {a: u.get("value") or 0 for a, u in zip(agents, per_agent)},
    }
