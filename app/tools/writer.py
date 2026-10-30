"""Writer's tools: the cited why-now story, outreach drafts, and the founder's decisions on drafts."""

import json
import re
from typing import Annotated, Literal

from pydantic import Field

from app import db
from app.connectors import ollama
from app.models import EmailDraft, Founder, Outreach, Profile, Story
from app.prompts import DIR as PROMPTS_DIR

STORY_SYSTEM = (PROMPTS_DIR / "story.md").read_text()
OUTREACH_SYSTEM = (PROMPTS_DIR / "outreach.md").read_text()

MAX_WORDS = 90
MAX_NOTE_CHARS = 300
BANNED = [
    "hope this finds you well", "hope you're well", "hope you're doing well", "hope you are well", "i wanted to reach out", "reaching out", "circle back", "touch base",
    "synergy", "leverage", "game-changer", "game changer", "revolutionize", "cutting-edge", "best-in-class",
    "quick question", "just following up", "per my last email", "great fit", "perfect fit",
]
PLACEHOLDER = re.compile(r"\[[^\]]*\]|\{[^}]*\}")
WHERE = "the Approve tab in First100"


def _words(text: str) -> int:
    return len(text.split())


# --- story -----------------------------------------------------------------

def _facts(lead: dict) -> str:
    return "\n".join(
        f"[{i}] \"{e['quote']}\" ({e['signal_type']}{', ' + e['published_at'][:7] if e.get('published_at') else ''})"
        for i, e in enumerate(lead["evidence"], 1)
    )


def _check_story(story: Story, n_facts: int) -> list[str]:
    problems = []
    least = min(2, n_facts)  # one verified fact makes an honest one-line story
    if not least <= len(story.sentences) <= 4:
        problems.append(f"write {least} to 4 sentences, not {len(story.sentences)}")
    for s in story.sentences:
        if not s.refs or any(not 1 <= r <= n_facts for r in s.refs):
            problems.append(f'"{s.text[:60]}" must cite facts numbered 1 to {n_facts}')
    return problems


async def _write_story(lead: dict) -> list[dict]:
    """2-4 sentences, each citing evidence ids. One retry with the problems spelled out; then uncited lines are dropped."""
    facts = lead["evidence"]
    prompt = (
        f"Company: {lead['company']}\n"
        f"Contact: {lead['person_name']}{', ' + lead['title'] if lead['title'] else ''}\n"
        + (f"Connection to the founder: {lead['warm_path']}\n" if lead["warm_path"] else "")
        + f"\nFacts:\n{_facts(lead)}\n\nWrite the story."
    )
    story = await ollama.generate(prompt, Story, system=STORY_SYSTEM)
    if problems := _check_story(story, len(facts)):
        story = await ollama.generate(
            f"{prompt}\n\nYour last answer had problems: {'; '.join(problems)}. Fix them.", Story, system=STORY_SYSTEM,
        )
    return [
        {"text": s.text.strip(), "refs": sorted({facts[r - 1]["id"] for r in s.refs})}
        for s in story.sentences[:4]
        if s.text.strip() and s.refs and all(1 <= r <= len(facts) for r in s.refs)
    ]


# --- drafts ----------------------------------------------------------------

def _cliches(*texts: str) -> list[str]:
    return [b for b in BANNED if any(b in t.lower() for t in texts)]


def _check_email(e: EmailDraft, first_name: str) -> list[str]:
    problems = []
    if (n := _words(e.body)) > MAX_WORDS:
        problems.append(f"the email is {n} words; keep it under {MAX_WORDS}")
    if hits := _cliches(e.body, e.subject):
        problems.append(f"remove the clichés: {', '.join(hits)}")
    if "\n" not in e.body.strip():
        problems.append("put blank lines between the greeting, paragraphs and sign-off")
    if PLACEHOLDER.search(e.body) or PLACEHOLDER.search(e.subject):
        problems.append("replace placeholders in [brackets] or {braces} with real words")
    if first_name and first_name.lower() not in e.body.lower()[:60]:
        problems.append(f"greet {first_name} by first name")
    return problems


def _check_outreach(o: Outreach, first_name: str, not_theirs: list[str]) -> list[str]:
    problems = [f"signal_email: {p}" for p in _check_email(o.signal_email, first_name)]
    problems += [f"pain_email: {p}" for p in _check_email(o.pain_email, first_name)]
    if len(o.linkedin_note) > MAX_NOTE_CHARS:
        problems.append(f"linkedin_note is {len(o.linkedin_note)} characters; keep it under {MAX_NOTE_CHARS}")
    if len(o.followups) < 2:
        problems.append("write 2 followups")
    if hits := _cliches(o.linkedin_note, *o.followups):
        problems.append(f"followups and linkedin_note: remove the clichés: {', '.join(hits)}")
    everything = " ".join([o.signal_email.body, o.pain_email.body, o.linkedin_note, *o.followups]).lower()
    if mixed := [n for n in not_theirs if n.lower() in everything]:
        problems.append(f"{', '.join(mixed)} has nothing to do with this lead; take it out")
    return problems


async def _write_outreach(lead: dict, story: list[dict], profile: Profile, founder: Founder,
                          feedback: str | None) -> tuple[Outreach, list[str]]:
    """Both email versions, follow-ups and the LinkedIn note. Returns any problems left after one retry.

    The founder's background only goes in through the warm path: given as loose context, a small model
    mixes the founder's old companies into the lead's news.
    """
    first_name = (lead["person_name"] or "").split()[0] if lead["person_name"] else ""
    warm = (lead["warm_path"] or "").lower()
    not_theirs = [n for n in founder.past_companies + founder.schools + founder.investors
                  if n.strip() and n.lower() not in warm and n.lower() not in lead["company"].lower()]
    prompt = (
        f"## The founder\nName: {founder.name}\n"
        f"Product: {profile.product}\nProblems it fixes: {'; '.join(profile.pains)}\n\n"
        f"## The lead\nCompany: {lead['company']}\nContact: {lead['person_name']}"
        f"{', ' + lead['title'] if lead['title'] else ''} (first name: {first_name})\n"
        + (f"Connection to the founder: {lead['warm_path']}\n" if lead["warm_path"] else "")
        + f"Why now: {' '.join(s['text'] for s in story)}\n"
        + (f"\n## The founder's feedback on the last draft\n{feedback}\n" if feedback else "")
        + "\nWrite the drafts."
    )
    outreach = await ollama.generate(prompt, Outreach, system=OUTREACH_SYSTEM)
    if problems := _check_outreach(outreach, first_name, not_theirs):
        outreach = await ollama.generate(
            f"{prompt}\n\nYour last drafts had problems: {'; '.join(problems)}. Fix them.", Outreach, system=OUTREACH_SYSTEM,
        )
    return outreach, _check_outreach(outreach, first_name, not_theirs)


# --- tools -----------------------------------------------------------------

async def draft_outreach(
    lead_id: int,
    feedback: Annotated[str | None, Field(description="The founder's feedback when rewriting a draft")] = None,
) -> dict:
    """Write the cited why-now story and the outreach drafts for a researched lead: two email versions, follow-ups
    and a LinkedIn note.

    The drafts go to the Approve tab in the First100 web app, where the founder reviews them.
    Pass `feedback` to rewrite a lead's drafts; anything not yet sent is replaced.
    """
    lead = db.get_lead(lead_id)
    if lead is None:
        return {"error": f"No lead {lead_id}."}
    if not lead["tier"]:
        return {"error": f"{lead['company']} (lead {lead_id}) hasn't been researched yet."}
    if not lead["person_name"]:
        return {"error": f"Research found nobody to write to at {lead['company']} (lead {lead_id})."}
    if not lead["evidence"]:
        return {"error": f"Nothing verified about {lead['company']} (lead {lead_id}) to write from; it needs more research."}
    _, profile, _ = db.get_profile()
    founder = db.get_founder()

    try:
        story = await _write_story(lead)
        if not story:
            return {"error": f"Couldn't write a story for {lead['company']} where every line is backed by a source."}
        db.update_lead(lead_id, story_json=json.dumps(story))
        outreach, problems = await _write_outreach(lead, story, profile, founder, feedback)
    except Exception as e:  # Ollama down or bad output twice
        return {"error": f"Writing for {lead['company']} (lead {lead_id}) failed: {e}"}

    followups = json.dumps([f.strip() for f in outreach.followups[:2]])
    db.replace_drafts(lead_id, [
        {"channel": "email", "variant": "A", "angle": "signal", "subject": outreach.signal_email.subject.strip(),
         "body": outreach.signal_email.body.strip(), "followups_json": followups},
        {"channel": "email", "variant": "B", "angle": "pain", "subject": outreach.pain_email.subject.strip(),
         "body": outreach.pain_email.body.strip(), "followups_json": followups},
        {"channel": "linkedin", "variant": "A", "angle": "signal", "body": outreach.linkedin_note.strip()[:MAX_NOTE_CHARS]},
    ])
    result = {
        "lead_id": lead_id,
        "company": lead["company"],
        "to": lead["person_name"],
        "story": [s["text"] for s in story],
        "drafts": [
            {"version": "A", "opens_with": "their news", "subject": outreach.signal_email.subject,
             "words": _words(outreach.signal_email.body)},
            {"version": "B", "opens_with": "a problem", "subject": outreach.pain_email.subject,
             "words": _words(outreach.pain_email.body)},
        ],
        "where": WHERE,
    }
    if problems:
        result["warnings"] = problems  # shown so the founder can fix them while editing
    return result


def _pending_email(lead_id: int, version: str) -> dict | None:
    return next((d for d in db.list_drafts(lead_id)
                 if d["channel"] == "email" and d["variant"] == version and d["status"] in ("pending", "approved")), None)


async def approve_draft(
    lead_id: int,
    version: Annotated[Literal["A", "B"], Field(description="Which email version: A opens with their news, "
                                                             "B with a problem")] = "A",
    send: Annotated[bool, Field(description="True only if the founder also said to send it now")] = False,
) -> dict:
    """Approve one of a lead's email versions (the other is dropped), and send it if the founder said so.

    Sending is simulated. Approved emails can also be sent from the Approve tab.
    """
    draft = _pending_email(lead_id, version)
    if draft is None:
        return {"error": f"No version {version} draft waiting for lead {lead_id}."}
    db.set_draft_status(draft["id"], "approved")  # retires the other version
    if send:
        db.set_draft_status(draft["id"], "sent")
    return {"lead_id": lead_id, "version": version, "status": "sent" if send else "approved", "simulated": send}


async def reject_draft(lead_id: int) -> dict:
    """Throw away all of a lead's drafts that haven't been sent."""
    drafts = [d for d in db.list_drafts(lead_id) if d["status"] in ("pending", "approved")]
    if not drafts:
        return {"error": f"No drafts waiting for lead {lead_id}."}
    for d in drafts:
        db.set_draft_status(d["id"], "rejected")
    return {"lead_id": lead_id, "status": "rejected", "drafts": len(drafts)}
