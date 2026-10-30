"""Hunter: the people and emails at a company, and whether an email is deliverable. Cached like every external call."""

from __future__ import annotations

import httpx

from app import config
from app.connectors.cache import cached

URL = "https://api.hunter.io/v2"


class NoKey(RuntimeError):
    pass


async def _get(path: str, params: dict) -> dict:
    async def fetch() -> dict:
        if not config.HUNTER_API_KEY:
            raise NoKey("Set HUNTER_API_KEY in .env to look up contacts.")
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.get(f"{URL}/{path}", params={**params, "api_key": config.HUNTER_API_KEY})
            response.raise_for_status()
            return response.json().get("data") or {}

    return await cached("hunter", {"path": path, **params}, fetch)


async def domain_search(*, domain: str | None = None, company: str | None = None) -> dict:
    """{"domain", "organization", "emails": [{"value", "first_name", "last_name", "position", "seniority",
    "confidence", "verification": {"status"}}]}. Pass the domain if known, else the company name. Costs one search."""
    params = {"domain": domain} if domain else {"company": company}
    return await _get("domain-search", {**params, "type": "personal", "limit": 10})


async def verify(email: str) -> str:
    """'valid', 'risky' (accepts anything or a webmail address), 'invalid' or 'unknown'. Costs one verification."""
    status = (await _get("email-verifier", {"email": email})).get("status")
    return {"valid": "valid", "accept_all": "risky", "webmail": "risky", "invalid": "invalid"}.get(status, "unknown")
