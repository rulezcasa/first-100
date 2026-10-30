"""Researcher's tools: evidence, score, contact and warm path for a lead."""

import json
import re
from datetime import date, datetime, timezone
from typing import Annotated
from urllib.parse import urlparse

from pydantic import Field

from app import db
from app.connectors import hunter, ollama, tavily
from app.models import Founder, NetworkFindings, Profile, ResearchFindings
from app.prompts import DIR as PROMPTS_DIR

RESEARCH_SYSTEM = (PROMPTS_DIR / "research.md").read_text()
NETWORK_SYSTEM = (PROMPTS_DIR / "network.md").read_text()

MAX_ARTICLES = 5
ARTICLE_CHARS = 1000  # per article: Tavily's snippet plus the page text around the company's name
MAX_EVIDENCE = 5

# Score = fit (0-40, the model's judgement) + recency (0-40) + contactability (0-20).
TIER_A, TIER_B = 70, 45
CONTACT_POINTS = {"valid": 20, "risky": 12, "unknown": 8}
RECENCY_UNKNOWN = 15  # there is evidence, but no page says when


# --- reading pages ---------------------------------------------------------

def _norm(text: str) -> str:
    """Compare text the way a reader would: case, curly quotes, dashes and spacing don't matter."""
    text = text.lower().translate(str.maketrans("‘’“”–—", "''\"\"--"))
    return " ".join(text.split())


def _window(text: str, name: str, chars: int) -> str:
    """The part of a page around the first mention of `name`."""
    at = max(text.lower().find(name.lower()), 0)
    start = max(at - chars // 4, 0)
    return text[start:start + chars]


async def _pages(query: str, name: str, *, time_range: str | None) -> list[dict]:
    """Search, keeping pages that mention `name`. Each gets "text" (what the model reads) and "full" (to check quotes)."""
    pages = []
    for r in await tavily.search(query, max_results=MAX_ARTICLES + 2, time_range=time_range, raw=True):
        full = f"{r.get('title', '')}\n{r.get('content', '')}\n{r.get('raw_content') or ''}"
        if name.lower() not in full.lower():
            continue
        snippet = r.get("content", "")
        pages.append({
            **r,
            "full": full,
            "text": f"{snippet}\n…{_window(r.get('raw_content') or '', name, ARTICLE_CHARS - len(snippet[:ARTICLE_CHARS // 2]))}",
        })
    return pages[:MAX_ARTICLES]


def _listing(pages: list[dict]) -> str:
    return "\n\n".join(f"[{i}] {p['title']} ({urlparse(p['url']).hostname})\n{p['text']}" for i, p in enumerate(pages, 1))


def _page(pages: list[dict], number: int) -> dict | None:
    return pages[number - 1] if 1 <= number <= len(pages) else None


# --- evidence and score ----------------------------------------------------

def _month(month: str, page_text: str) -> str | None:
    """The model's YYYY-MM, kept only if that year is actually on the page."""
    m = re.fullmatch(r"(20\d\d)-(0[1-9]|1[0-2])", month.strip())
    return f"{m.group(1)}-{m.group(2)}-01" if m and m.group(1) in page_text else None


async def _find_evidence(lead: dict, profile: Profile, correction: str | None) -> tuple[ResearchFindings, list[dict]]:
    """Search the company, have the model pick quotes and judge fit; keep only quotes found word for word."""
    company = lead["company"]
    query = f'"{company}" {correction or lead["industry"] or ""}'.strip()
    pages = await _pages(query, company, time_range="year")
    scout_found = "; ".join(e["quote"] for e in lead["evidence"])[:400]
    site = f" ({lead['domain']})" if lead["domain"] else ""
    prompt = (
        f"Founder's product: {profile.product}\n"
        f"Who should buy it: {'; '.join(s.name for s in profile.segments) or ', '.join(profile.industries)}\n"
        f"Problems it fixes: {'; '.join(profile.pains)}\n\n"
        f"Company: {company}{site}, found in the group \"{lead['industry']}\"\n"
        + (f"What Scout found: {scout_found}\n" if scout_found else "")
        + (f"The founder's correction (earlier research was wrong): {correction}\n" if correction else "")
        + f"\n## Articles\n{_listing(pages) or '(no pages found)'}\n\nWrite the findings for {company}."
    )
    findings = await ollama.generate(prompt, ResearchFindings, system=RESEARCH_SYSTEM)

    known = {_norm(e["quote"]) for e in lead["evidence"]}
    evidence = []
    for item in findings.evidence:
        page = _page(pages, item.article)
        quote = item.quote.strip()
        if page is None or len(quote) < 20 or _norm(quote) not in _norm(page["full"]) or _norm(quote) in known:
            continue  # not on the page word for word, or already a source
        known.add(_norm(quote))
        evidence.append({
            "url": page["url"],
            "title": page.get("title") or "",
            "quote": quote[:400],
            "signal_type": item.signal_type,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": tavily.published(page) or _month(item.month, page["full"]) or _date_in(quote),
        })

    # A domain only counts if a page shows it and it's the company's, not the publisher's.
    domain = findings.domain.strip().lower().removeprefix("www.")
    shown = any(domain in p["full"].lower() or domain in p["url"] for p in pages)
    findings.domain = domain if domain and shown and _looks_like(domain, company) else ""
    return findings, evidence


def _looks_like(domain: str, company: str) -> bool:
    """pigtailsandcrewcuts.com looks like Pigtails & Crewcuts; 1851franchise.com, the site that wrote about it, doesn't."""
    host = re.sub(r"[^a-z0-9]", "", domain.lower().rsplit(".", 1)[0])
    name = db.norm_name(company).removeprefix("the ")
    return bool(host) and (name.replace(" ", "") in host or host in name.replace(" ", "")
                           or any(len(w) >= 4 and w in host for w in name.split()))


MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
          "november", "december"]


def _date_in(quote: str) -> str | None:
    """'In August 2026 Phenix launched…' -> 2026-08-01: the quote's own month and year, if it has one."""
    m = re.search(rf"\b({'|'.join(MONTHS)})\s+(20\d\d)\b", quote.lower())
    return f"{m.group(2)}-{MONTHS.index(m.group(1)) + 1:02d}-01" if m else None


def _recency(evidence: list[dict]) -> int:
    dates = [date.fromisoformat(d[:10]) for e in evidence if (d := e.get("published_at") or _date_in(e["quote"]))]
    if not dates:
        return RECENCY_UNKNOWN if evidence else 0
    days = (date.today() - max(dates)).days
    return 40 if days <= 45 else 30 if days <= 120 else 20 if days <= 240 else 10 if days <= 365 else 5


def _tier(score: int, evidence: list[dict]) -> str:
    if not evidence:
        return "C"  # nothing verifiable means no reason to write to them now
    return "A" if score >= TIER_A else "B" if score >= TIER_B else "C"


# --- contact ---------------------------------------------------------------

def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]+", text.lower()))


def _pick_contact(emails: list[dict], buyer_roles: list[str]) -> dict | None:
    """The person whose title best matches who buys, then the most senior, then Hunter's most confident."""
    role_words = set().union(*(_words(r) for r in buyer_roles)) - {"of", "and", "the"} if buyer_roles else set()

    def rank(e: dict) -> tuple:
        position = (e.get("position") or "").lower()
        exact = any(r.lower() in position for r in buyer_roles)
        return (exact, len(role_words & _words(position)), {"executive": 2, "senior": 1}.get(e.get("seniority"), 0),
                e.get("confidence") or 0)

    people = [e for e in emails if e.get("value") and e.get("first_name")]
    return max(people, key=rank, default=None)


async def _find_contact(company: str, domain: str | None, buyer_roles: list[str]) -> tuple[dict | None, str | None]:
    """(contact, the company's domain per Hunter). Contact: {name, title, email, email_status}."""
    found = await hunter.domain_search(domain=domain, company=company)
    if not found.get("domain") or not _looks_like(found["domain"], company):
        return None, None  # Hunter matched a different company
    person = _pick_contact(found.get("emails") or [], buyer_roles)
    if person is None:
        return None, found["domain"]
    status = (person.get("verification") or {}).get("status")
    status = "valid" if status == "valid" else await hunter.verify(person["value"])
    contact = {
        "name": f"{person['first_name']} {person.get('last_name') or ''}".strip(),
        "title": person.get("position"),
        "email": None if status == "invalid" else person["value"],
        "email_status": None if status == "invalid" else status,
    }
    return contact, found["domain"]


# --- warm path -------------------------------------------------------------

ALIASES = {"yc": "y combinator", "a16z": "andreessen horowitz", "mit": "massachusetts institute of technology"}


def _same(a: str, b: str) -> bool:
    """'Stanford' matches 'Stanford University' and 'YC' matches 'Y Combinator'; short names must match exactly."""
    a, b = (ALIASES.get(db.norm_name(x), db.norm_name(x)) for x in (a, b))
    if not a or not b:
        return False
    return a == b or (min(len(a), len(b)) >= 5 and (a in b or b in a))


def _sentence_with(text: str, name: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return next((s for s in sentences if name.lower() in s.lower()), _window(text, name, 240))[:300]


async def _find_warm_path(lead: dict, person: str | None, founder: Founder) -> tuple[dict | None, dict]:
    """Search the person's background and the company's investors; return the first link to the founder.

    Returns (warm path {sentence, via, evidence}, everything found). Names count only if the page says them.
    """
    company = lead["company"]
    for past in founder.past_companies:  # the founder used to work there: no search needed
        if _same(past, company):
            return {"sentence": f"You used to work at {company}", "via": {"kind": "Company", "name": company}}, {}

    pages = []
    if person:
        pages += await _pages(f'"{person}" {company} background', person, time_range=None)
    pages += await _pages(f'"{company}" investors funding', company, time_range=None)
    if not pages:
        return None, {}
    prompt = (
        f"Company: {company}\nContact person: {person or '(unknown)'}\n\n"
        f"## Articles\n{_listing(pages)}\n\nWrite what the articles say."
    )
    found = await ollama.generate(prompt, NetworkFindings, system=NETWORK_SYSTEM)

    def real(facts) -> list[tuple[str, dict]]:
        return [(f.name.strip(), p) for f in facts if (p := _page(pages, f.article)) and f.name.strip()
                and _norm(f.name) in _norm(p["full"])]

    network = {k: [n for n, _ in real(getattr(found, k))] for k in ("past_companies", "schools", "investors")}
    checks = [
        ("Company", real(found.past_companies), founder.past_companies, "You and {person} both worked at {name}"),
        ("School", real(found.schools), founder.schools, "You and {person} both studied at {name}"),
        ("Investor", real(found.investors), founder.investors, "{name} backs both you and {company}"),
    ]
    for kind, facts, mine, sentence in checks:
        for name, page in facts:
            if any(_same(name, m) for m in mine):
                return {
                    "sentence": sentence.format(person=person, name=name, company=company),
                    "via": {"kind": kind, "name": name},
                    "evidence": {
                        "url": page["url"], "title": page.get("title") or "", "quote": _sentence_with(page["full"], name),
                        "signal_type": "other", "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "published_at": tavily.published(page),
                    },
                }, network
    return None, network


# --- tools -----------------------------------------------------------------

async def research_lead(
    lead_id: int,
    correction: Annotated[str | None, Field(description="The founder's correction if earlier research was "
                                                        "wrong, e.g. 'that's a different Acme, the one in Dallas'")] = None,
) -> dict:
    """Check a lead's buying signals against real sources, score it (tier A/B/C, 0-100) and find the best contact.

    Returns the verified evidence with source links, tier, score, contact and any warm path to the founder.
    Pass `correction` to redo research that was wrong; earlier sources are ignored.
    """
    lead = db.get_lead(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    _, profile, _ = db.get_profile()
    if correction:
        db.reject_evidence(lead_id)
        lead["evidence"] = []

    try:
        findings, new_evidence = await _find_evidence(lead, profile, correction)
        domain = lead["domain"] or findings.domain or None
        contact, hunter_domain = await _find_contact(lead["company"], domain, profile.buyer_roles)
        domain = domain or hunter_domain
    except (tavily.NoKey, hunter.NoKey) as e:
        return {"error": str(e)}
    except Exception as e:  # Tavily, Hunter or Ollama down: say so rather than guess
        return {"error": f"Research on {lead['company']} (lead {lead_id}) failed: {e}"}

    db.add_evidence(lead_id, new_evidence)
    evidence = lead["evidence"] + new_evidence
    fit = max(0, min(findings.fit if findings.fit <= 40 else round(findings.fit * 0.4), 40))  # "85" on a 0-100 scale
    parts = {"fit": fit, "recency": _recency(evidence), "contact": CONTACT_POINTS.get((contact or {}).get("email_status"), 0)}
    score = sum(parts.values())
    tier = _tier(score, evidence)

    warm, network = None, {}
    founder = db.get_founder()
    if tier in ("A", "B") and (founder.past_companies or founder.schools or founder.investors):
        try:
            warm, network = await _find_warm_path(lead, contact and contact["name"], founder)
        except Exception:
            pass  # a warm path is a bonus; the research stands without it
        if warm and warm.get("evidence"):
            db.add_evidence(lead_id, [warm["evidence"]])

    db.update_lead(
        lead_id,
        domain=domain,
        person_name=contact and contact["name"],
        title=contact and contact["title"],
        email=contact and contact["email"],
        email_status=contact and contact["email_status"],
        tier=tier,
        score=score,
        warm_path=warm and warm["sentence"],
        research_json=json.dumps({
            "score_parts": parts, "fit_reason": findings.fit_reason.strip(),
            "warm_via": warm and warm["via"], "network": network, "correction": correction,
        }),
    )
    result = {
        "lead_id": lead_id,
        "company": lead["company"],
        "tier": tier,
        "score": score,
        "score_parts": parts,
        "fit": findings.fit_reason.strip(),
        "evidence": [{"quote": e["quote"], "url": e["url"], "signal_type": e["signal_type"], "date": e.get("published_at")}
                     for e in evidence][:MAX_EVIDENCE],
        "contact": contact,
        "warm_path": warm and warm["sentence"],
    }
    if not evidence:
        result["note"] = "Nothing recent could be verified from real sources."
    elif tier == "C":
        result["note"] = "Weak lead: consider skipping it."
    return result


async def skip_lead(
    lead_id: int,
    reason: Annotated[str, Field(description="Why it's being dropped, in a few words")],
) -> dict:
    """Drop a lead: it won't get outreach."""
    lead = db.get_lead(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    research = json.loads(lead["research_json"] or "{}")
    db.update_lead(lead_id, stage="skipped", research_json=json.dumps({**research, "skip_reason": reason}))
    return {"lead_id": lead_id, "company": lead["company"], "stage": "skipped"}
