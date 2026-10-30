"""Sample leads, outcomes, AI usage and deals so the Dashboard has something to show.

Run from the repo root: `.venv/bin/python -m app.scripts.seed_dashboard`
Running it again does nothing; pass --reset to delete the sample rows first.
Flexprice can't delete events, so after a --reset it holds the old sample usage as well as the new.
"""

from __future__ import annotations

import json
import random
import sys

from app import db, usage

MARK = "sample"  # leads.source can't hold it, so sample leads are tagged in research_json

# Same segments (and industry labels) as the real leads, so the reply-rate chart groups them together.
SALONS = "Independent beauty salons and wellness clinics"
BEAUTY = "SMEs in the beauty and wellness industry"
RETAIL = "Retail SMEs with limited operational resources"

LEADS = [
    # company, industry, person, title, tier, score, stage, outcome, deal (status, value)
    ("Glow Theory Studio", SALONS, "Maya Brooks", "Owner", "A", 84, "sent", "meeting", ("confirmed", 2400)),
    ("Lumen Skin Clinic", SALONS, "Daniel Reyes", "Clinic Director", "A", 81, "sent", "meeting", ("confirmed", 3600)),
    ("The Hair Atelier", SALONS, "Sofia Marchetti", "Founder", "A", 78, "sent", "replied", ("potential", 1800)),
    ("Bloom Wellness Spa", SALONS, "Grace Kim", "Spa Manager", "B", 70, "sent", "meeting", ("potential", 3000)),
    ("Velvet Nail Bar", SALONS, "Aisha Rahman", "Owner", "B", 62, "sent", "no_reply", None),
    ("Serenity Day Spa", BEAUTY, "Hannah Lewis", "Operations Manager", "A", 76, "sent", "meeting", ("confirmed", 4200)),
    ("Pure Aesthetics Group", BEAUTY, "Marcus Hall", "COO", "B", 68, "sent", "replied", ("lost", 2500)),
    ("Kindred Beauty Co", BEAUTY, "Olivia Tran", "Head of Operations", "B", 64, "sent", "no_reply", None),
    ("Halo Brow & Lash", BEAUTY, "Zoe Adams", "Founder", "C", 52, "sent", "no_reply", None),
    ("Corner Page Books", RETAIL, "Peter Walsh", "Store Manager", "B", 60, "sent", "replied", ("potential", 1500)),
    ("Hearth & Home Goods", RETAIL, "Laura Bennett", "Owner", "B", 58, "sent", "no_reply", None),
    ("Nomad Outdoor Supply", RETAIL, "Ethan Cole", "Ops Lead", "C", 47, "sent", "no_reply", None),
    ("Rosewood Salon", SALONS, "Chloe Martin", "Owner", "A", 80, "drafted", None, None),
    ("Willow Wellness", BEAUTY, "Isabel Cruz", "Clinic Manager", "B", 66, "drafted", None, None),
    ("Fable Bookshop", RETAIL, "Noah Grant", "Owner", "C", 44, "found", None, None),
]

AGENTS = {"Scout": (30, 2500, 300), "Researcher": (55, 4000, 600), "Writer": (40, 3000, 450), "Learner": (6, 3500, 400), "tool": (90, 1800, 350)}


def reset() -> None:
    with db.connect() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM leads WHERE research_json LIKE ?", (f'%"{MARK}": true%',))]
        for table in ("deals", "outcomes", "drafts"):
            c.executemany(f"DELETE FROM {table} WHERE lead_id = ?", [(i,) for i in ids])
        c.executemany("DELETE FROM leads WHERE id = ?", [(i,) for i in ids])
        c.execute("DELETE FROM usage WHERE props_json LIKE ?", (f'%"{MARK}": true%',))


def seed() -> None:
    db.init()
    if "--reset" in sys.argv:
        reset()
    with db.connect() as c:
        if c.execute("SELECT 1 FROM leads WHERE research_json LIKE ?", (f'%"{MARK}": true%',)).fetchone():
            print("Sample data already there (use --reset to replace it)")
            return

    rng = random.Random(100)
    lead_ids = []
    with db.connect() as c:
        for company, industry, person, title, tier, score, stage, outcome, deal in LEADS:
            domain = company.lower().replace(" & ", "").replace(" ", "") + ".com"
            lead_id = c.execute(
                "INSERT INTO leads (company, domain, industry, person_name, title, email, email_status, tier, score, stage, profile_version, research_json) "
                "VALUES (?, ?, ?, ?, ?, ?, 'valid', ?, ?, ?, 1, ?)",
                (company, domain, industry, person, title, f"{person.split()[0].lower()}@{domain}", tier, score, stage, json.dumps({MARK: True})),
            ).lastrowid
            lead_ids.append(lead_id)
            if outcome:
                c.execute("INSERT INTO outcomes (lead_id, outcome) VALUES (?, ?)", (lead_id, outcome))
                # Signal emails do better in the sample, so the angle chart has a clear winner.
                angle = "signal" if (outcome != "no_reply") == (rng.random() < 0.75) else "pain"
                c.execute(
                    "INSERT INTO drafts (lead_id, channel, variant, angle, subject, body, status) VALUES (?, 'email', 'A', ?, ?, ?, 'sent')",
                    (lead_id, angle, f"Quick idea for {company}", f"Hi {person.split()[0]}, sample {angle} email."),
                )
            if deal:
                c.execute("INSERT INTO deals (lead_id, status, value_usd) VALUES (?, ?, ?)", (lead_id, *deal))

        for agent, (calls, avg_in, avg_out) in AGENTS.items():
            for _ in range(calls):
                tin, tout = int(avg_in * rng.uniform(0.5, 1.5)), int(avg_out * rng.uniform(0.5, 1.5))
                days_ago = rng.choices(range(14), weights=[14 - d for d in range(14)])[0]  # the last two weeks, busier lately
                c.execute(
                    "INSERT INTO usage (event_name, lead_id, agent, props_json, cost_usd, created_at) "
                    "VALUES ('llm.call', ?, ?, ?, ?, datetime('now', ?, ?))",
                    (rng.choice(lead_ids), agent, json.dumps({"input_tokens": tin, "output_tokens": tout, MARK: True}), usage.llm_cost(tin, tout),
                     f"-{days_ago} days", f"-{rng.randint(0, 600)} minutes"),
                )
    print(f"Added {len(LEADS)} sample leads with outcomes, deals and AI usage")


if __name__ == "__main__":
    seed()
