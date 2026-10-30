"""In-memory stand-ins for the database and external APIs, so the team can run end to end.

Each tool module swaps its use of this for db.py / Tavily / Hunter / Ollama as
those get built. Delete this file when nothing imports it.
"""

PROFILE = {
    "version": 1,
    "product": "Inventory tracking for mid-size warehouses",
    "who_should_buy": ["logistics companies (50-500 people)", "3PL warehouses", "e-commerce fulfillment"],
    "buying_signals": ["opening a new warehouse", "hiring inventory or ops managers", "recent funding"],
    "filters": [],
    "change_note": None,
}

# What discovery "finds" on the web.
CANDIDATES = [
    {"company": "Acme Freight", "domain": "acmefreight.com", "industry": "logistics",
     "signal": "announced a new Dallas warehouse (Oct 2026)"},
    {"company": "Boxly Logistics", "domain": "boxly.io", "industry": "logistics",
     "signal": "a 2023 press release about expansion"},
]

# What research "finds" per domain.
RESEARCH = {
    "acmefreight.com": {
        "evidence": [
            {"claim": "Opened a second warehouse in Dallas", "url": "https://example.com/acme-dallas", "date": "2026-10-02"},
            {"claim": "Hiring 2 inventory managers", "url": "https://example.com/acme-jobs", "date": "2026-10-20"},
        ],
        "tier": "A", "score": 87,
        "contact": {"name": "Jane Doe", "title": "COO", "email": "jane@acmefreight.com", "email_status": "valid"},
        "warm_path": "Founder and Jane both worked at Stripe",
    },
    "boxly.io": {
        "evidence": [], "tier": "C", "score": 31, "contact": None, "warm_path": None,
        "note": "Only source is a 2023 press release; nothing recent could be verified.",
    },
}

LEADS: dict[int, dict] = {}   # lead_id -> lead (company fields + research + stage)
DRAFTS: dict[int, dict] = {}  # lead_id -> draft

OUTCOMES = {
    "by_industry": {"logistics": {"sent": 11, "replied": 5}, "retail": {"sent": 8, "replied": 1}},
    "by_angle": {"signal": {"sent": 13, "replied": 5}, "pain": {"sent": 6, "replied": 1}},
}
