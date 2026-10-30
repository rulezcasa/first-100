"""API routes. Setup so far: the founder describes their product in a chat; each turn fills in the form.

The chat is a draft held by the browser: /setup/chat saves nothing. Only /setup/finalize writes to the
database; the page opens on what was last finalized (GET /setup) until the founder starts over (DELETE /setup).
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.connectors import ollama
from app.models import Founder, Product, SetupTurn
from app.prompts import DIR as PROMPTS_DIR

router = APIRouter(prefix="/setup", tags=["setup"])

SYSTEM = (PROMPTS_DIR / "setup.md").read_text()

# What setup must capture, in the order Scout asks (each is described in prompts/setup.md).
# 'founder.background' is done once any of past companies, schools or investors is filled.
REQUIRED = [
    "product.product",
    "product.buyer_roles",
    "product.industries",
    "product.pains",
    "founder.background",
    "founder.name",
]


class Message(BaseModel):
    role: Literal["founder", "scout"]
    text: str


class ChatIn(BaseModel):
    """The browser's draft plus the founder's new message."""

    text: str
    messages: list[Message]
    product: Product
    founder: Founder
    hand_edited: list[str] = []  # 'product.<field>' / 'founder.<field>': the model can't change these
    skipped: list[str] = []  # REQUIRED details the founder chose to skip


class ChatOut(BaseModel):
    reply: str
    product: Product
    founder: Founder
    skipped: list[str]


class FinalizeIn(BaseModel):
    messages: list[Message]
    product: Product
    founder: Founder
    skipped: list[str] = []


def _still_needed(product: Product, founder: Founder, skipped: list[str]) -> list[str]:
    """Required details that are empty and not skipped. Whether a filled one is specific enough is the LLM's call."""
    filled = {f"product.{k}": bool(v) for k, v in product.model_dump().items()}
    filled |= {f"founder.{k}": bool(v) for k, v in founder.model_dump().items()}
    filled["founder.background"] = bool(founder.past_companies or founder.schools or founder.investors)
    return [k for k in REQUIRED if not filled[k] and k not in skipped]


def _as_required(keys: list[str]) -> list[str]:
    """Map what the model wrote ('pains', 'background') onto REQUIRED keys; drop anything else."""
    by_name = {k.split(".")[1]: k for k in REQUIRED}
    out = [k if k in REQUIRED else by_name.get(k.split(".")[-1]) for k in keys]
    return [k for k in REQUIRED if k in out]


PLACEHOLDERS = {"unknown", "n/a", "na", "none", "not provided", "not specified", "tbd", "-"}


def _clean(model: BaseModel):
    """Small models sometimes write 'Unknown' instead of leaving a field empty."""
    fixed: dict = {}
    for k, v in model.model_dump().items():
        if isinstance(v, str) and v.strip().lower() in PLACEHOLDERS:
            fixed[k] = ""
        elif isinstance(v, list):
            fixed[k] = [x for x in v if not (isinstance(x, str) and x.strip().lower() in PLACEHOLDERS)]
    return model.model_copy(update=fixed)


def _keep_locked(prefix: str, current: BaseModel, proposed: BaseModel, locks: set[str]):
    """The LLM's version of the form, with every hand-edited field put back."""
    keep = {k: getattr(current, k) for k in type(current).model_fields if f"{prefix}.{k}" in locks}
    return proposed.model_copy(update=keep)


@router.post("/chat")
async def chat(body: ChatIn) -> ChatOut:
    """One turn: Scout replies and proposes the updated form. Nothing is saved."""
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Say something about your product first.")

    still_needed = _still_needed(body.product, body.founder, body.skipped)
    # Earlier turns go in as real chat messages, so the model sees what it already asked.
    history = [{"role": "user" if m.role == "founder" else "assistant", "content": m.text} for m in body.messages]
    # This turn: the form state, then the new message last (small local models weigh the end most).
    prompt = (
        f"## The form as it currently reads\n"
        f"Product: {body.product.model_dump_json()}\n"
        f"Founder: {body.founder.model_dump_json()}\n"
        f"Still empty: {', '.join(still_needed) or 'nothing'}\n"
        f"Skipped by the founder: {', '.join(body.skipped) or 'none'}\n\n"
        f"## The founder's new message\n{text}"
    )
    try:
        turn = await ollama.generate(prompt, SetupTurn, system=SYSTEM, history=history)
    except Exception as e:  # Ollama not running, bad output twice: the founder can just resend
        raise HTTPException(502, f"Scout couldn't answer just now: {e}") from e

    locks = set(body.hand_edited)
    return ChatOut(
        reply=turn.reply,
        product=_keep_locked("product", body.product, _clean(turn.product), locks),
        founder=_keep_locked("founder", body.founder, _clean(turn.founder), locks),
        # Once skipped, a detail stays skipped; the founder can still fill it in the form.
        skipped=_as_required(body.skipped + turn.skipped),
    )


class SavedOut(BaseModel):
    saved: bool  # False before the first finalize, or after starting over
    messages: list[Message]
    product: Product
    founder: Founder
    skipped: list[str]


@router.get("")
def saved() -> SavedOut:
    """What was last finalized, so the page can open on it."""
    _, profile, _ = db.get_profile()
    product = Product.model_validate(profile.model_dump())
    founder = db.get_founder()
    # Skips aren't stored, but finalize only allows an empty required detail if it was skipped.
    return SavedOut(
        saved=bool(product.product),
        messages=[Message(role=m["role"], text=m["text"]) for m in db.setup_messages()],
        product=product,
        founder=founder,
        skipped=_still_needed(product, founder, []),
    )


@router.delete("")
def start_over() -> dict:
    """Delete everything setup saved, so the team starts from nothing."""
    db.clear_setup()
    return {"cleared": True}


@router.post("/finalize")
def finalize(body: FinalizeIn) -> dict:
    """Save the product, the founder's background and the conversation. The team works from this."""
    missing = _still_needed(body.product, body.founder, body.skipped)
    if missing:
        raise HTTPException(400, f"Still missing: {', '.join(missing)}")
    _, profile, _ = db.get_profile()
    update = body.product.model_dump()
    if Product.model_validate(profile.model_dump()) != body.product:
        # The product changed, so Scout's groups no longer match it: the Who page works them out again.
        update |= {"segments": [], "expansion": [], "competitors": []}
    db.save_profile(profile.model_copy(update=update))
    db.save_founder(body.founder)
    db.replace_setup_messages([m.model_dump() for m in body.messages])
    return {"finalized": True}
