"""Tavily web search: a query in, recent pages (title, url, text) out. Cached like every external call."""

from __future__ import annotations

from email.utils import parsedate_to_datetime

import httpx

from app import config
from app.connectors.cache import cached

URL = "https://api.tavily.com/search"


class NoKey(RuntimeError):
    pass


async def search(
    query: str, *, max_results: int = 8, topic: str = "general", time_range: str | None = "month", raw: bool = False,
) -> list[dict]:
    """Each result: {"title", "url", "content", "published_date"?, "raw_content"? (with `raw`), "score"}.

    A recent `time_range` favours announcements (funding, openings, hires): buying signals. `topic="general"`
    finds more company-specific pages than "news", which leans towards big outlets and trend pieces.
    """
    request = {"query": query, "max_results": max_results, "topic": topic, "time_range": time_range}
    if time_range is None:
        del request["time_range"]  # any date
    if raw:
        request["include_raw_content"] = True  # the page's full text, to check quotes against

    async def fetch() -> list[dict]:
        if not config.TAVILY_API_KEY:
            raise NoKey("Set TAVILY_API_KEY in .env to search the web.")
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.post(URL, headers={"Authorization": f"Bearer {config.TAVILY_API_KEY}"}, json=request)
            response.raise_for_status()
            return response.json().get("results", [])

    return await cached("tavily", request, fetch)


def published(result: dict) -> str | None:
    """The page's publish date as YYYY-MM-DD, when Tavily knows it (mostly news pages)."""
    try:
        return parsedate_to_datetime(result["published_date"]).date().isoformat()
    except (KeyError, TypeError, ValueError):
        try:
            return result["published_date"][:10] if result.get("published_date") else None
        except TypeError:
            return None
