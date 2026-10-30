# First100

**An AI sales engine for founders doing their first 100 sales.**

A founder describes their product in plain words. First100 works out who should buy it, finds real companies and decision-makers on the public web, explains *why each lead fits right now* with a cited story, drafts short founder-voice outreach for approval, and learns from replies which customers and message angles work.

## What makes us different

1. **The cited "why now" story.** Every lead comes with a short explanation of why this company, and why now. Every sentence links to a real source, so nothing is made up.
2. **Learning from replies.** The engine tracks which industries and email styles get replies. It then suggests where to focus next ("Logistics replied 3× more"). The founder accepts or rejects each suggestion, and the next search uses it.
3. **Built for founders doing their first 100 sales.**
   - Plain language instead of sales jargon.
   - Small batches of high-quality leads.
   - Short emails in the founder's own voice.
   - Warm paths first: leads connected to the founder's past employers, school, or investors are flagged.

## Planned feature: Snap Lead

Take a picture of a business card at a networking event and feed it straight into the lead workflow. First100 reads the card, finds the company, and runs it through the same research, cited story, and drafting steps as any other lead.

---

## Demos
**Pitch** : https://drive.google.com/file/d/1EyZ5pciGv1oLJvuKdAPuPfYEBVosEEJO/view?usp=sharing
<br>
**Demo** : https://drive.google.com/file/d/1dxhA-f5OmfgOp_wh-j0mphnv5Rdso0qw/view

## Problem statement

Early-stage founders have to sell before they can afford a sales team, and most of them have never done it. The usual tools don't fit:

- **Sales tools assume a sales team.** CRMs and lead databases expect you to already know your ideal customer profile, speak in jargon ("ICP", "accounts", "sequences"), and send at volume.
- **AI outreach is untrustworthy.** Generic AI SDRs hallucinate facts about prospects and send templated spam that burns a founder's reputation, which is their most valuable early asset.
- **No feedback loop.** Founders rarely track which customer types and message angles actually get replies, so they keep guessing.
- **Warm paths go unused.** A founder's own background (past employers, school, investors) is often the best way in, but nobody connects it to prospects.

First100 addresses this with the three differentiators above.

---

## Pipeline

```
 ┌────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌──────────────┐
 │ 1. Setup   │──▶│ 2. Who should buy │──▶│ 3. Discover  │──▶│ 4. Research  │
 │ chat+form  │   │ segments, conf.,  │   │ Tavily signal│   │ evidence,    │
 │ → Profile  │   │ competitors       │   │ queries      │   │ score, Hunter│
 └────────────┘   └──────────────────┘   └──────────────┘   │ contact, graph│
                                                            └──────┬───────┘
 ┌────────────┐   ┌──────────────────┐   ┌──────────────┐   ┌──────▼───────┐
 │ 8. Learn   │◀──│ 7. Outcomes      │◀──│ 6. Approve & │◀──│ 5. Write     │
 │ insights → │   │ replied/no reply/│   │    send      │   │ cited story, │
 │ profile v2 │   │ meeting          │   │ (founder)    │   │ A/B drafts   │
 └─────┬──────┘   └──────────────────┘   └──────────────┘   └──────────────┘
       └──────────────── next discovery uses profile v2 ───────────────▲
```

| Step | Agent | What happens | Guardrail |
|---|---|---|---|
| Setup | Scout | Chat/form text → `Profile` (product, buyer roles, industries, pains) + `Founder` background | Pydantic-constrained JSON output |
| Who should buy | Scout | Profile → 2–4 segments with confidence, expansion segments, competitors | Confidence shown as High/Med/Low |
| Discover | Scout | Segment + signal keywords → Tavily searches → candidate companies | Dedupe by normalized name |
| Evidence | Researcher | 1–2 Tavily searches with raw content → `{claim, url, quote, signal_type}` | Quote must be a substring of fetched text |
| Score | Researcher | Fit (40) + signal recency (40) + contactability (20) → 0–100, Tier A/B/C | Fixed rubric |
| Contact | Researcher | Hunter domain search → best title match → email verifier | `valid / risky / unknown` badge |
| Network | Researcher | Person/company background → `PREVIOUSLY_WORKED_AT`, `STUDIED_AT`, `BACKED_BY` edges | Edges only from fetched text |
| Story | Writer | Evidence → "why now" story with `[n]` footnotes | Retry if a sentence lacks a valid ref |
| Drafts | Writer | Lead + story + founder background + angle (signal/pain) → email A/B, follow-ups, LinkedIn note | <90 words, banned-phrase list |
| Approve | Founder | Approve / edit / reject each draft | Nothing sends without approval |
| Outcomes | Simulator | `POST /simulate` rolls replies biased by industry + angle | Gives the demo a clear winner |
| Learn | Learner | Reply rate by industry & angle → one proposal → profile v2 | Needs ≥5 outcomes |

---

## Architecture

```
┌──────────────────────── webapp/ (Vite + React + TS + Tailwind) ───────────────────────┐
│ Setup · Who · Leads (drawer + force graph) · Approve · Pipeline · Dashboard           │
│ "Do this next" banner · Agent activity panel (SSE)                                     │
└───────────────────────────────┬───────────────────────────────────────────────────────┘
                                │ REST + SSE  (:5173 → :8000)
┌───────────────────────────────▼──────────────── app/ (FastAPI) ───────────────────────┐
│ api/  routes · leads · who · activity                                                  │
│                                                                                        │
│ Band room (band/bridge.py, room.py) ── mention-routed messages ──┐                     │
│   @Team ─▶ @Scout ─▶ @Researcher ─▶ @Writer ─▶ founder ─▶ @Learner │ founder can steer │
│   Each agent = prompt (prompts/*.md) + tools (tools/*.py)          │ any agent live    │
│   running on OllamaAdapter (band/ollama_adapter.py)               ─┘                   │
│                                                                                        │
│ tools/  scout · researcher · writer · learner · shared   (return data, never prose)    │
│ connectors/  cache.py ─▶ ollama · tavily · hunter · flexprice                          │
│ db.py (SQLite) · graph.py (Neo4j) · events.py (SSE bus) · usage.py (cost metering)     │
└──────┬───────────────┬───────────────┬───────────────┬───────────────┬────────────────┘
       ▼               ▼               ▼               ▼               ▼
   Ollama          Tavily          Hunter       Neo4j Aura        SQLite
 (qwen2.5:7b)   (web search)    (contacts)   (knowledge graph)  (app state)
```

### Agents

Agents are teammates in one Band room. An @mention wakes an agent. Its LLM reads the room, calls tools if it needs to, then replies or hands work to a teammate by @mentioning them. Routing comes from the prompts, not hardcoded flows. The fixed, guarded steps live *inside* tools, so the LLM picks which step to run but can't skip validation.

| Agent | Tools |
|---|---|
| Team | Band messaging only (founder's front door) |
| Scout | `get_profile`, `suggest_segments`, `add_filter`, `find_companies`, `find_lookalikes`, `list_leads` |
| Researcher | `research_lead`, `skip_lead`, `get_lead`, `list_leads` |
| Writer | `draft_outreach`, `approve_draft`, `reject_draft`, `get_lead`, `list_leads` |
| Learner | `analyze_outcomes`, `update_profile` |

### Data

- **SQLite:** profiles (versioned), founder, leads, evidence, drafts, outcomes, activity, usage, cache.
- **Neo4j graph:** `Founder`, `Company`, `Person`, `Signal`, `School`, `Investor` nodes with `WORKS_AT`, `PREVIOUSLY_WORKED_AT`, `STUDIED_AT`, `BACKED_BY`, `HAS_SIGNAL`, `CONTACTED`, `REPLIED`. Used for **warm paths** (e.g. "you both worked at Stripe"), **lookalikes**, and the per-lead subgraph.
- **Cache:** every Ollama/Tavily/Hunter call inside a tool goes through `connectors/cache.py`, keyed by request hash and stored in `app/data/cache/`. `DEMO_MODE` replays from cache, so the demo works offline.
- **Cost metering:** each external call is recorded in `usage` and synced to Flexprice, giving cost per lead, per reply, and per meeting.

---

## Getting started

Prerequisites: Python 3.11+, Node 18+, [Ollama](https://ollama.com) running locally.

```bash
ollama pull qwen2.5:7b
```

```bash
cp .env.example .env   # fill in Tavily, Hunter, Neo4j, Band (and optional Flexprice) keys
```

Backend:

```bash
uvicorn app.main:app --reload
```

Frontend:

```bash
cd webapp && npm install && npm run dev
```

Open http://localhost:5173.

### Environment

| Variable | Purpose |
|---|---|
| `OLLAMA_URL`, `OLLAMA_MODEL` | Local LLM for all calls |
| `TAVILY_API_KEY` | Web search with page content (citations) |
| `HUNTER_API_KEY` | Contact lookup + email verification |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | Knowledge graph |
| `BAND_API_KEY`, `BAND_ROOM_ID` | Agent room |
| `FLEXPRICE_API_KEY` | Optional cost metering sync |
| `DEMO_MODE` | `live` or cache replay |

---

## Repo layout

```
app/
  main.py config.py models.py db.py
  agents/team.py        agent = prompt + tools
  prompts/              shared.md + one .md per agent/step
  tools/                one file per agent + shared.py
  api/                  routes, leads, who, activity
  band/                 Band bridge, room, Ollama adapter
  connectors/           cache, ollama, tavily, hunter
  data/cache/           replayable API responses
webapp/
  src/pages/            Setup, Who, Leads, Approve, Pipeline, Dashboard
```
