-- App state (PLAN.md §2). Lists and nested objects are stored as JSON text.

CREATE TABLE IF NOT EXISTS profiles (
    id          INTEGER PRIMARY KEY,
    version     INTEGER NOT NULL UNIQUE,
    json        TEXT NOT NULL,              -- models.Profile
    change_note TEXT,
    created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS founder (
    id   INTEGER PRIMARY KEY CHECK (id = 1),  -- one founder per app
    json TEXT NOT NULL                         -- models.Founder
);

CREATE TABLE IF NOT EXISTS setup_messages (     -- the conversation behind the finalized setup
    id         INTEGER PRIMARY KEY,
    role       TEXT NOT NULL CHECK (role IN ('founder', 'scout')),
    text       TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id              INTEGER PRIMARY KEY,
    company         TEXT NOT NULL,
    domain          TEXT,
    industry        TEXT,
    person_name     TEXT,
    title           TEXT,
    email           TEXT,
    email_status    TEXT CHECK (email_status IN ('valid', 'risky', 'unknown')),
    tier            TEXT CHECK (tier IN ('A', 'B', 'C')),
    score           INTEGER,
    story_json      TEXT,
    profile_version INTEGER,
    stage           TEXT NOT NULL DEFAULT 'found',
    source          TEXT NOT NULL DEFAULT 'ai' CHECK (source IN ('ai', 'founder')),
    warm_path       TEXT,                    -- "You and Jane both worked at Stripe"
    research_json   TEXT,                    -- score breakdown, fit reason, warm_via, network found
    updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id          INTEGER PRIMARY KEY,
    lead_id     INTEGER NOT NULL REFERENCES leads(id),
    url         TEXT NOT NULL,
    title       TEXT,
    quote       TEXT NOT NULL,
    signal_type TEXT,
    fetched_at  TEXT,
    published_at TEXT,                      -- when the page says it happened, if known (YYYY-MM-DD)
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'rejected'))
);

CREATE TABLE IF NOT EXISTS drafts (
    id      INTEGER PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    channel TEXT NOT NULL CHECK (channel IN ('email', 'linkedin')),
    variant TEXT CHECK (variant IN ('A', 'B')),
    angle   TEXT CHECK (angle IN ('signal', 'pain')),
    subject TEXT,
    body    TEXT NOT NULL,
    followups_json TEXT,                    -- email only: nudges if there's no reply
    status  TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'sent'))
);

CREATE TABLE IF NOT EXISTS outcomes (
    lead_id   INTEGER NOT NULL REFERENCES leads(id),
    outcome   TEXT NOT NULL CHECK (outcome IN ('replied', 'no_reply', 'meeting')),
    logged_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS activity (
    id         INTEGER PRIMARY KEY,
    agent      TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS usage (
    id         INTEGER PRIMARY KEY,
    event_name TEXT NOT NULL,
    lead_id    INTEGER,
    agent      TEXT,
    props_json TEXT,
    cost_usd   REAL NOT NULL DEFAULT 0,
    cached     INTEGER NOT NULL DEFAULT 0,
    synced     INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (                -- a lead the founder is talking to about buying
    lead_id    INTEGER PRIMARY KEY REFERENCES leads(id),
    status     TEXT NOT NULL CHECK (status IN ('potential', 'confirmed', 'lost')),
    value_usd  REAL NOT NULL DEFAULT 0,          -- expected for potential, agreed for confirmed
    note       TEXT,
    synced_at  TEXT,                             -- last sent to Flexprice (confirmed deals only)
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
