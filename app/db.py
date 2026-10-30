"""SQLite app state. One file, one connection per call, no ORM."""

from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app import config
from app.models import Founder, Profile

DB_PATH = config.ROOT / "app" / "data" / "first100.db"
SCHEMA = Path(__file__).parent / "schema.sql"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Columns added after the first databases were made; CREATE TABLE IF NOT EXISTS won't add them.
_ADDED_COLUMNS = [("leads", "warm_path", "TEXT"), ("leads", "research_json", "TEXT"), ("evidence", "published_at", "TEXT"),
                  ("drafts", "followups_json", "TEXT"), ("deals", "synced_at", "TEXT")]


def init() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript(SCHEMA.read_text())
        for table, column, kind in _ADDED_COLUMNS:
            try:
                c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
            except sqlite3.OperationalError:
                pass  # already there


# --- target profile -------------------------------------------------------

def get_profile() -> tuple[int, Profile, str | None]:
    """The latest profile as (version, profile, change_note); an empty v1 before setup."""
    with connect() as c:
        row = c.execute("SELECT version, json, change_note FROM profiles ORDER BY version DESC LIMIT 1").fetchone()
    if row is None:
        return 1, Profile(), None
    return row["version"], Profile.model_validate_json(row["json"]), row["change_note"]


def save_profile(profile: Profile, *, new_version: bool = False, change_note: str | None = None) -> int:
    """Overwrite the latest version (setup edits, filters) or add the next one (Learner). Returns the version."""
    with connect() as c:
        row = c.execute("SELECT version FROM profiles ORDER BY version DESC LIMIT 1").fetchone()
        if row is None or new_version:
            version = (row["version"] + 1) if row else 1
            c.execute(
                "INSERT INTO profiles (version, json, change_note) VALUES (?, ?, ?)",
                (version, profile.model_dump_json(), change_note),
            )
        else:
            version = row["version"]
            c.execute("UPDATE profiles SET json = ? WHERE version = ?", (profile.model_dump_json(), version))
    return version


def profile_history() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT version, change_note, created_at FROM profiles ORDER BY version").fetchall()
    return [dict(r) for r in rows]


# --- leads ----------------------------------------------------------------

_SUFFIXES = re.compile(r"\b(inc|llc|ltd|limited|corp|corporation|co|company|gmbh|plc|sa|ag|group|holdings)\b")


def norm_name(name: str) -> str:
    """'Stripe, Inc.' and 'stripe' are the same company."""
    name = re.sub(r"[^\w\s]", " ", name.lower())
    return " ".join(_SUFFIXES.sub(" ", name).split())


def _lead(c: sqlite3.Connection, row: sqlite3.Row) -> dict:
    evidence = c.execute(
        "SELECT id, url, title, quote, signal_type, fetched_at, published_at FROM evidence "
        "WHERE lead_id = ? AND status = 'active' ORDER BY id",
        (row["id"],),
    ).fetchall()
    return {**dict(row), "evidence": [dict(e) for e in evidence]}


def list_leads() -> list[dict]:
    """Every lead with its active evidence, newest first."""
    with connect() as c:
        return [_lead(c, r) for r in c.execute("SELECT * FROM leads ORDER BY id DESC").fetchall()]


def get_lead(lead_id: int) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        return _lead(c, row) if row else None


def known_companies() -> set[str]:
    """Normalized names of every lead so far, so discovery never adds the same company twice."""
    with connect() as c:
        return {norm_name(r["company"]) for r in c.execute("SELECT company FROM leads").fetchall()}


def add_lead(lead: dict, evidence: list[dict]) -> int:
    """Save a new lead (leads columns) with its evidence (evidence columns, minus lead_id). Returns its id."""
    with connect() as c:
        cols = ", ".join(lead)
        lead_id = c.execute(f"INSERT INTO leads ({cols}) VALUES ({', '.join('?' * len(lead))})", tuple(lead.values())).lastrowid
        _insert_evidence(c, lead_id, evidence)
    return lead_id


def _insert_evidence(c: sqlite3.Connection, lead_id: int, evidence: list[dict]) -> list[int]:
    return [
        c.execute(
            "INSERT INTO evidence (lead_id, url, title, quote, signal_type, fetched_at, published_at) "
            "VALUES (:lead_id, :url, :title, :quote, :signal_type, :fetched_at, :published_at)",
            {"published_at": None, **e, "lead_id": lead_id},
        ).lastrowid
        for e in evidence
    ]


def add_evidence(lead_id: int, evidence: list[dict]) -> list[int]:
    with connect() as c:
        return _insert_evidence(c, lead_id, evidence)


def reject_evidence(lead_id: int) -> None:
    """The founder said earlier research was wrong: hide its sources from the lead."""
    with connect() as c:
        c.execute("UPDATE evidence SET status = 'rejected' WHERE lead_id = ?", (lead_id,))


def update_lead(lead_id: int, **fields) -> None:
    with connect() as c:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        c.execute(f"UPDATE leads SET {sets}, updated_at = CURRENT_TIMESTAMP WHERE id = :id", {**fields, "id": lead_id})


def set_lead_stage(lead_id: int, stage: str) -> None:
    with connect() as c:
        c.execute("UPDATE leads SET stage = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (stage, lead_id))


# --- drafts ---------------------------------------------------------------

def list_drafts(lead_id: int | None = None) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT * FROM drafts" + (" WHERE lead_id = ?" if lead_id else "") + " ORDER BY id", (lead_id,) if lead_id else (),
        ).fetchall()
    return [dict(r) for r in rows]


def get_draft(draft_id: int) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return dict(row) if row else None


def replace_drafts(lead_id: int, drafts: list[dict]) -> list[int]:
    """A new set of drafts for a lead: anything not yet sent is replaced."""
    with connect() as c:
        c.execute("DELETE FROM drafts WHERE lead_id = ? AND status != 'sent'", (lead_id,))
        return [
            c.execute(
                "INSERT INTO drafts (lead_id, channel, variant, angle, subject, body, followups_json) "
                "VALUES (:lead_id, :channel, :variant, :angle, :subject, :body, :followups_json)",
                {"variant": None, "angle": None, "subject": None, "followups_json": None, **d, "lead_id": lead_id},
            ).lastrowid
            for d in drafts
        ]


def edit_draft(draft_id: int, subject: str | None, body: str | None) -> None:
    with connect() as c:
        c.execute("UPDATE drafts SET subject = COALESCE(?, subject), body = COALESCE(?, body) WHERE id = ?",
                  (subject, body, draft_id))


def set_draft_status(draft_id: int, status: str) -> None:
    """Approving one email version retires the lead's other pending one and moves the lead to Approved."""
    with connect() as c:
        d = c.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
        if d is None:
            return
        c.execute("UPDATE drafts SET status = ? WHERE id = ?", (status, draft_id))
        if status == "approved" and d["channel"] == "email":
            c.execute("UPDATE drafts SET status = 'rejected' WHERE lead_id = ? AND channel = 'email' AND id != ? "
                      "AND status = 'pending'", (d["lead_id"], draft_id))
            c.execute("UPDATE leads SET stage = 'approved', updated_at = CURRENT_TIMESTAMP "
                      "WHERE id = ? AND stage = 'found'", (d["lead_id"],))
        if status == "sent" and d["channel"] == "email":
            c.execute("UPDATE leads SET stage = 'sent', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (d["lead_id"],))


def send_approved() -> list[int]:
    """'Send' every approved email (simulated). Returns the lead ids sent to."""
    ids = [d["id"] for d in list_drafts() if d["status"] == "approved" and d["channel"] == "email"]
    for draft_id in ids:
        set_draft_status(draft_id, "sent")
    return [get_draft(i)["lead_id"] for i in ids]


# --- founder --------------------------------------------------------------

def get_founder() -> Founder:
    with connect() as c:
        row = c.execute("SELECT json FROM founder WHERE id = 1").fetchone()
    return Founder.model_validate_json(row["json"]) if row else Founder()


def save_founder(founder: Founder) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO founder (id, json) VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET json = excluded.json",
            (founder.model_dump_json(),),
        )


# --- setup chat -----------------------------------------------------------

def setup_messages() -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT role, text, created_at FROM setup_messages ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def replace_setup_messages(messages: list[dict]) -> None:
    """Store the setup conversation as finalized, replacing the previous one."""
    with connect() as c:
        c.execute("DELETE FROM setup_messages")
        c.executemany("INSERT INTO setup_messages (role, text) VALUES (:role, :text)", messages)


def clear_setup() -> None:
    """Start over: forget the product, the founder and the setup conversation, and every profile version."""
    with connect() as c:
        c.execute("DELETE FROM setup_messages")
        c.execute("DELETE FROM founder")
        c.execute("DELETE FROM profiles")
