"""Scout's tools: the target profile and finding companies that fit."""

import random
import re
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlparse

from pydantic import Field

from app import db
from app.connectors import ollama, tavily
from app.models import FoundCompanies, Profile, Segment, WhoShouldBuy
from app.prompts import DIR as PROMPTS_DIR

WHO_SYSTEM = (PROMPTS_DIR / "who.md").read_text()
DISCOVER_SYSTEM = (PROMPTS_DIR / "discover.md").read_text()

# Each group is searched for a different kind of buying signal per round; a round adds one search per group.
# A run stops once it has enough new leads, so the next run (searches are cached) carries on where it stopped.
SIGNAL_QUERIES = ["opens new location", "raises funding", "expands and hires", "appoints new CEO"]
MAX_GROUPS = 3  # so at most MAX_GROUPS * len(SIGNAL_QUERIES) Tavily calls per run
ARTICLE_CHARS = 600  # keeps a page of results inside a small local model's context


async def get_profile() -> dict:
    """Get the current target profile: the product, who buys it, the groups who should buy it, and the founder's filters."""
    version, profile, change_note = db.get_profile()
    if not profile.product:
        return {"error": "Setup isn't finished: the founder hasn't described the product yet."}
    return {"version": version, "change_note": change_note, **profile.model_dump()}


def _tidy(answer: WhoShouldBuy, profile: Profile) -> WhoShouldBuy:
    """Guard a small model's answer: sane confidences, 2-4 distinct groups, and 2 expansions that are new."""
    seen: set[str] = set()
    segments: list[Segment] = []
    for s in answer.segments:
        key = s.name.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        confidence = s.confidence / 100 if s.confidence > 1 else s.confidence  # "84" instead of 0.84
        segments.append(Segment(name=s.name.strip(), why=s.why.strip(), confidence=min(max(confidence, 0.05), 0.95)))
    segments = sorted(segments, key=lambda s: s.confidence, reverse=True)[:4]

    taken = seen | {i.strip().lower() for i in profile.industries}
    expansion = []
    for e in answer.expansion:
        if e.strip() and e.strip().lower() not in taken:
            taken.add(e.strip().lower())
            expansion.append(e.strip())
    return WhoShouldBuy(segments=segments, expansion=expansion[:2])


async def suggest_segments(
    again: Annotated[bool, Field(description="True to get a different answer from the last one")] = False,
) -> dict:
    """Work out who should buy the product: 2-4 groups of companies with a confidence each, plus 2 nearby groups to try.

    Saves them to the current target profile, replacing any earlier suggestion.
    """
    version, profile, _ = db.get_profile()
    if not profile.product:
        return {"error": "Setup isn't finished: there's no product to work from yet."}
    prompt = (
        "Founder's product:\n"
        f"- What it is: {profile.product}\n"
        f"- Who buys it: {', '.join(profile.buyer_roles)}\n"
        f"- Industries: {', '.join(profile.industries)}\n"
        f"- Problems it fixes: {'; '.join(profile.pains)}\n\n"
        "Write the answer for this product."
    )
    variant = random.randint(1, 2**31) if again else 0
    answer = _tidy(await ollama.generate(prompt, WhoShouldBuy, system=WHO_SYSTEM, variant=variant), profile)
    if not answer.segments:
        return {"error": "Scout couldn't come up with any groups. Try again."}
    db.save_profile(profile.model_copy(update={"segments": answer.segments, "expansion": answer.expansion}))
    return {"version": version, **answer.model_dump()}


async def add_filter(
    rule: Annotated[str, Field(description="The rule in plain words, e.g. 'skip companies under 50 people'")],
) -> dict:
    """Save a rule for which companies to include or skip. It applies from the next search."""
    _, profile, _ = db.get_profile()
    filters = [*profile.filters, rule] if rule not in profile.filters else profile.filters
    db.save_profile(profile.model_copy(update={"filters": filters}))
    return {"saved": rule, "filters": filters}


def _clean_domain(domain: str) -> str | None:
    domain = domain.strip().lower()
    if not domain:
        return None
    host = urlparse(domain if "//" in domain else f"//{domain}").hostname or ""
    host = host.removeprefix("www.")
    return host if "." in host else None


def _quote(signal: str, text: str, company: str) -> str:
    """The evidence must be the page's own words: the model's sentence if it's really there, else the page's."""
    if signal and " ".join(signal.lower().split()) in " ".join(text.lower().split()):
        return signal.strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return next((x for x in sentences if company.lower() in x.lower()), sentences[0])[:300].strip()


async def _search_group(group: str, query: str, profile: Profile, known: set[str]) -> list[dict]:
    """One Tavily search, then the model picks out companies; keeps only ones the articles really name."""
    articles = [a for a in await tavily.search(query) if a.get("content")]
    if not articles:
        return []
    listing = "\n\n".join(
        f"[{i}] {a['title']} ({urlparse(a['url']).hostname})\n{a['content'][:ARTICLE_CHARS]}" for i, a in enumerate(articles, 1)
    )
    prompt = (
        f"Founder's product: {profile.product}\n"
        f"Who buys it: {', '.join(profile.buyer_roles)}\n"
        f"Group searched: {group}\n"
        f"Founder's rules: {'; '.join(profile.filters) or 'none'}\n\n"
        f"## Articles\n{listing}\n\n"
        "List the companies that fit."
    )
    answer = await ollama.generate(prompt, FoundCompanies, system=DISCOVER_SYSTEM)

    found = []
    for c in answer.companies:
        key = db.norm_name(c.company)
        if not key or key in known or not 1 <= c.article <= len(articles):
            continue
        article = articles[c.article - 1]
        text = f"{article['title']}. {article['content']}"
        if key not in db.norm_name(text):  # the model named a company the article doesn't
            continue
        known.add(key)
        found.append({
            "company": c.company.strip(),
            "domain": _clean_domain(c.domain),
            "group": group,
            "evidence": {
                "url": article["url"],
                "title": article["title"],
                "quote": _quote(c.signal, article["content"], c.company),
                "signal_type": c.signal_type,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "published_at": tavily.published(article),
            },
        })
    return found


async def find_companies(
    limit: Annotated[int, Field(description="How many new companies to look for")] = 5,
) -> dict:
    """Search the web for companies that match the profile and show a recent buying signal.

    Each company found is saved as a new lead (shown in the founder's Leads tab); returns them with their lead ids,
    the signal that made each look promising and its source.
    """
    version, profile, _ = db.get_profile()
    if not profile.product:
        return {"error": "Setup isn't finished: there's no product to search for yet."}
    groups = [s.name for s in profile.segments] or profile.industries
    if not groups:
        return {"error": "There are no groups to search yet. Work out who should buy first (suggest_segments)."}

    known = db.known_companies()
    candidates, searched = [], []
    try:
        searches = [
            (group, f"{group} {SIGNAL_QUERIES[(i + r) % len(SIGNAL_QUERIES)]}")
            for r in range(len(SIGNAL_QUERIES)) for i, group in enumerate(groups[:MAX_GROUPS])
        ]
        for group, query in searches:
            searched.append(query)
            candidates += await _search_group(group, query, profile, known)
            if len(candidates) >= limit:
                break
    except tavily.NoKey as e:
        return {"error": str(e)}
    except Exception as e:  # Tavily or Ollama down: report it rather than guess
        if not candidates:
            return {"error": f"The web search failed: {e}", "searched": searched}

    found = []
    for c in candidates[:limit]:
        lead_id = db.add_lead(
            {"company": c["company"], "domain": c["domain"], "industry": c["group"], "profile_version": version},
            [c["evidence"]],
        )
        found.append({
            "lead_id": lead_id, "company": c["company"], "domain": c["domain"], "group": c["group"],
            "signal": c["evidence"]["quote"], "source": c["evidence"]["url"],
        })
    result: dict = {"found": found, "searched": searched}
    if not found:
        result["note"] = "Nothing new that fits turned up in these searches."
    return result


async def find_lookalikes() -> dict:
    """Find companies similar to the ones whose people replied."""
    # TODO: graph.lookalikes()
    return {"error": "Lookalike search isn't available yet."}
