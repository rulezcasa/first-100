# First100 — Hackathon Development Plan

Source of truth for *what* to build: [context.md](context.md). This file is *how* and *in what order*, sized for one day (~11 working hours).

---

## 0. Guiding rules for the day

1. **Demo path first, breadth later.** One founder → profile → 5–10 cited leads → drafts → approve → simulated replies → insight → profile v2. If that loop works end-to-end by hour 7, everything else is bonus.
2. **Every external call has a cached fallback.** Tavily/Hunter/LLM responses are written to `app/data/cache/*.json` keyed by request hash. The live demo replays from cache if Wi-Fi or rate limits fail.
3. **Seed a demo founder.** One hard-coded intake (e.g. a warehouse-inventory SaaS founder, ex-Stripe, Stanford, backed by YC) so warm paths actually show up on stage.
4. **No auth, one user, one backend process.** FastAPI runs the API, the Band agents and the Flexprice sync. SQLite for app state, Neo4j only for the graph.

### Repo layout
```
app/       FastAPI backend   → uvicorn app.main:app --reload   (port 8000)
  main.py config.py models.py db.py schema.sql graph.py events.py usage.py simulator.py
  agents/    team.py: each agent = prompt + the tools it may use
  prompts/   shared.md (context for every agent) + one <agent>.md per agent
  tools/     plain async functions, one file per agent (scout.py, researcher.py, writer.py, learner.py) + shared.py
  api/       routes.py (setup now; leads, outreach, insights, activity to come)
  connectors/ cache.py (shared wrapper), ollama.py, tavily.py, hunter.py, flexprice.py
  band/      bridge.py + ollama_adapter.py (runs every agent on a local Ollama model), agent_config.yaml (gitignored)
  data/      cache/, seed/demo-founder.json
  scripts/   seed.py
webapp/    Vite + React frontend → npm run dev                  (port 5173)
  src/pages/       Setup, Who, Leads, Approve, Pipeline, Insights
  src/components/  layout/, setup/, who/, leads/, approve/, pipeline/, insights/, ui/
  src/api.ts  src/types.ts  src/copy.ts
```

---

## 1. Stack

| Concern | Choice | Why |
|---|---|---|
| Backend (`app/`) | **Python + FastAPI**, Pydantic models | Team's strongest language; most of the day is agent/data work |
| Frontend (`webapp/`) | **Vite + React + TypeScript**, react-router | Thin UI calling the API with `fetch` |
| UI | Tailwind + shadcn/ui | Fast drawers, tables, tooltips, kanban cards |
| App DB | **SQLite** via stdlib `sqlite3` | Zero setup; leads, drafts, outcomes, profile versions |
| Graph | **Neo4j Aura Free** + `neo4j` Python driver | `MERGE`, path queries for warm paths |
| Graph view | `react-force-graph-2d` | Drop-in force-directed graph |
| LLM | **Ollama** (local, `qwen2.5:7b` via `OLLAMA_MODEL`), JSON output constrained to Pydantic schemas | One local model for everything: the setup chat, the agents' own turns, and the work inside tools (extraction, scoring, drafts). No API keys or rate limits; the cache keeps repeat calls instant. |
| Web search | **Tavily** (`tavily-python`, `include_raw_content`) | Returns URLs + page text → citations |
| Contacts | **Hunter** (`domain-search`, `email-verifier`) via `httpx` | Person + email + verification status |
| Live activity | SSE (`sse-starlette`) from an in-process event bus; events also saved to SQLite | Powers the "agent activity" panel |
| Cost per lead (bonus) | Flexprice | See §7 |
| Agent handoffs | Band (`band-sdk`, Python), mention-routed messages in one room | Agents hand work to each other in the open; founder watches and steers. See §7 |

---

## 2. Data model

### SQLite (app state)
```
profiles     (id, version, json, change_note, created_at)          -- "Who should buy this", versioned
founder      (id, name, past_companies[], schools[], investors[])
leads        (id, company, domain, industry, person_name, title, email, email_status,
              tier, score, story_json, profile_version, stage, source: 'ai'|'founder',
              updated_at)                                          -- updated_at drives the Band handoff watchdog (§7)
evidence     (id, lead_id, url, title, quote, signal_type, fetched_at,
              status: active|rejected)                             -- rejected on redo; its URLs are excluded next time
drafts       (id, lead_id, channel: email|linkedin, variant: A|B, angle: signal|pain,
              subject, body, status: pending|approved|rejected|sent)
outcomes     (lead_id, outcome: replied|no_reply|meeting, logged_at)
activity     (id, agent, message, created_at)                      -- also streamed via SSE
usage        (id, event_name, lead_id?, agent, props_json, cost_usd, cached, synced, created_at)  -- §7 Flexprice
cache        (key, json)                                           -- request-hash → response
```

### Neo4j (graph) — exactly as in context.md §3
Name normalization helper `norm_name()` in `app/graph.py`: lowercase, strip punctuation and `inc|llc|ltd|corp|co|gmbh`, collapse whitespace. All writes use `MERGE` on `{key: norm_name(name)}`. The three queries from context.md live here as `warm_paths`, `lookalikes`, `lead_subgraph`.

---

## 3. The agents: teammates in a Band room

Four working agents (Scout, Researcher, Writer, Learner) plus a `Team` coordinator (the founder's front door: "@Team find leads"). A real agentic system: **each agent is an LLM with a prompt and a set of tools**, running on our `OllamaAdapter` (§7). Nothing is hardcoded about what an agent says or who it talks to.

**The model: agents are teammates who talk to each other.** Band only delivers messages: an @mention wakes the mentioned agent. When woken, the agent's LLM reads the room, calls its tools when and if it needs them, and then replies or hands work on by @mentioning a teammate. Anyone in the room (the founder or another agent) can ask any agent for something.

```
@mentioned by anyone
  Ollama (agent's prompt + recent room history + its tools)
    → calls tools as needed (research_lead, draft_outreach, …), sees results
    → band_send_message(text, mentions=[next teammate or whoever asked])
      or band_no_reply when nothing needs saying
```

**Three pieces, kept separate:**
- **Prompts** (`app/prompts/*.md`, Markdown) give context and goals, not scripts, so agents reason about each situation instead of matching phrases. `shared.md` is shared by every agent: the mission and the founder's situation (quality over volume, trust, their time, learning), what each teammate is good at, how teammates work together (mentions are how you hand off, push back or bring the founder in; name company + lead id; no acknowledgement chatter), and ground rules (facts only from tools). Each agent's own prompt describes its role, what good work looks like, and the judgment calls it owns. Routing emerges from that: e.g. Researcher knows weak leads protect nobody and strong ones need Writer.
- **Tools** (`app/tools/`) are plain async functions with typed parameters, one file per agent (`scout.py`, `researcher.py`, …) plus `shared.py` for lead lookups several agents use. They **return data, never prose**. The function name is the tool name, its docstring is what the LLM reads to decide when to call it, and its parameters (with `Annotated[..., Field(description=…)]` where useful) become the arguments; `tools.tool()` turns a function into a Band tool. The fixed, guarded pipeline steps (table below) live inside the tools, so the LLM chooses *which* step, never *how* it runs: quote verification and validators can't be skipped.
- **Team** (`app/agents/team.py`): each agent = its prompt + the functions it may call. Adding a capability = write a function in that agent's tools file and add it to the agent's list in `team.py`.

| Agent | Tools |
|---|---|
| Team | none (only Band messaging) |
| Scout | `get_profile`, `add_filter`, `find_companies`, `find_lookalikes`, `list_leads` |
| Researcher | `research_lead` (with optional founder `correction`), `skip_lead`, `get_lead`, `list_leads` |
| Writer | `draft_outreach` (with optional `feedback`), `approve_draft`, `reject_draft`, `get_lead`, `list_leads` |
| Learner | `analyze_outcomes`, `update_profile` |

**Shared code:**
- `connectors/cache.py`: one `cached()` wrapper used by Ollama, Tavily and Hunter calls *inside tools*. It handles caching, `DEMO_MODE` replay and cost tracking. (The agents' own chat turns go through `OllamaAdapter` and are not cached.)
- `connectors/ollama.py`: `generate(prompt, schema)` for structured calls inside tools (evidence extraction, scoring, stories, drafts).
- `graph.py`, `db.py`, `events.py`, `usage.py`: used by the tools; no agent talks to Neo4j, SQLite or Flexprice directly.

What the tools do inside (fixed code, guarded):

| Agent | Step | Input → Output | Key guardrail |
|---|---|---|---|
| **Scout** | build profile | chat/form text → `Profile` JSON (product, buyer roles, industries, pains) + `Founder` record | Pydantic `response_schema` |
| **Scout** | who should buy | Profile → 2–4 segments with `confidence` 0–1, 2 "expansion" segments, 3–5 competitors | Confidence shown as High/Med/Low in UI |
| **Scout** | find companies | Segment + signal keywords → Tavily queries (e.g. `"{industry}" "opens new warehouse" 2026`) → candidate companies | Dedupe by `norm_name` |
| **Researcher** | evidence | Company → 1–2 Tavily searches w/ raw content → evidence items `{claim, url, quote, signal_type}` | **Verify `quote` is a substring of fetched text**; drop otherwise |
| **Researcher** | score | Evidence + profile fit → score 0–100, Tier A/B/C | Simple rubric: fit (40) + signal recency (40) + contactability (20) |
| **Researcher** | contact | Domain → Hunter domain-search → best-matching person by title → email-verifier | Show `valid / risky / unknown` badge |
| **Writer** | why-now story | Evidence list → 2–4 sentence "why now" story, each sentence `[n]` refs | Reject & retry if any sentence lacks a ref or cites a non-existent id |
| **Researcher** | network (Tier A/B only) | 1 Tavily search for person background, 1 for company investors → `PREVIOUSLY_WORKED_AT`, `STUDIED_AT`, `BACKED_BY` edges with `evidence_id` | Extract only from fetched text; no edge if nothing found |
| **Writer** | drafts | Lead + story + founder background + random angle → email A/B + 2-step follow-up + LinkedIn note | <90 words check, banned-phrase list ("synergy", "circle back", "hope this finds you well"…), regenerate on fail |
| **Learner** | insights + proposal | Outcomes → reply rate by industry & angle → one proposal | Requires ≥ N outcomes (N=5 for demo) |

**Reply simulator** (`app/simulator.py`, `POST /simulate`): for each sent lead, roll an outcome with probabilities biased by industry + angle (e.g. logistics + signal = 45% reply). This guarantees the learning loop has a visible winner in the demo.

---

## 4. Screens

1. **Setup** — split view: chat on the left, live-filling form on the right (founder can edit any field). Includes "Your background" (past companies, school, investors) → feeds warm paths.
2. **Who should buy this** — segment cards with confidence, "Try also" expansion chips, competitor list. Button: **Find leads**.
3. **Leads** — table (company, person, tier, score, top signal, warm-path badge). Row → **Lead drawer**: cited story with clickable footnotes, evidence list, contact + verification, force graph, "Find more like these" (lookalikes).
4. **Approve** — queue of drafts; A/B side by side; Approve / Edit / Reject. LinkedIn note has "Copy" + "Mark sent".
5. **Pipeline** — kanban: Found → Approved → Sent → Replied → Meeting. Card shows `AI` or `You` attribution.
6. **Insights** — reply rate by industry and by angle (counts, best green / worst red), funnel numbers, the one proposal card with **Accept / Dismiss** → profile v2 + change note.
7. **Persistent chrome** — top "Do this next" banner (computed from state, e.g. "Approve 6 drafts"), right-side collapsible **Agent activity** feed.

Plain-language labels throughout (context.md D3). Keep `webapp/src/copy.ts` for all UI strings so wording is easy to review in one place.

---

## 5. Timeline (one day)

Assumes a team of 2–3; if solo, follow the hour blocks top to bottom and drop "Could" items.

| Time | Track A (backend/agents) | Track B (UI) | Track C (graph + bonus) |
|---|---|---|---|
| **H0–1** | FastAPI scaffold + CORS, env keys, SQLite schema, Pydantic models, cache wrapper for all external calls (with `track()` usage hook, §7), SSE event bus | Vite + React + Tailwind scaffold, layout shell, nav, "Do this next" banner, activity panel reading SSE | **Band echo test first** (§7): all 5 agents connect; one agent's mention wakes another. Then Neo4j Aura, `app/graph.py` with `norm_name`, `MERGE` helpers |
| **H1–3** | Intake + Who-should-buy agents; Scout + Researcher with quote verification, handing off via Band | Setup screen (chat + form), Who-should-buy screen | `band/bridge.py` + `handoff()` + watchdog; graph writes from discovery (Company, Person, Signal); Founder node from setup |
| **H3–5** | Researcher: score + contact (Hunter); Writer: cited story with validation | Leads table + drawer with footnoted story | Researcher network step; `warm_paths`, `lead_subgraph`; force graph in drawer |
| **H5–7** | Writer (A/B, angle, word/cliché checks); send (simulated) writes `CONTACTED` | Approval queue; Pipeline kanban | Reply simulator writes `REPLIED`; `lookalikes()` + "Find more like these" |
| **🔒 H7** | **Integration checkpoint: full loop works on the seeded founder.** Freeze the cache. | | |
| **H7–9** | Learner + proposal accept → profile v2 → re-run discovery uses v2 | Insights page, funnel, proposal card | Founder commands in Band ("approve", "@Scout skip under 50 people"); Learner → founder → Scout loop in the room |
| **H9–10** | Bug bash, prompt tuning on story/email quality; **last: Flexprice sync + cost numbers in UI (§7)** | Copy pass (plain language), empty states | Band message wording polish; help with Flexprice cost UI |
| **H10–11** | — | — | Demo rehearsal ×2 against cached data, record a backup video |

### Priority if time runs short
- **Must:** Band handoffs (§7, the pipeline runs on them), 1, 3, 6, 7 (cited story), 8 (approval), 9 (simulated send), 10 (pipeline), 11 (learning loop), 5 (graph view + warm paths)
- **Should:** 2 (confidence + expansion), 13 (activity panel), 12 (funnel)
- **Could:** 4 (competitors — one LLM call, cheap), A/B variants, LinkedIn note, real email send (Resend), bonus integrations

---

## 6. Demo script (3 min)

1. Paste the founder's one-paragraph pitch → profile fills live; activity panel narrates.
2. "Who should buy this" → click **Find leads**; watch Scout/Researcher in the feed.
3. Open top Tier A lead: read the cited story, click footnote [1] → real article. Show graph: *"You both worked at Stripe"* warm path highlighted.
4. Approve two drafts (edit one live). Send.
5. Hit **Simulate replies** → Pipeline moves. Insights: logistics + signal angle wins.
6. **Accept** "Focus on logistics, use signal emails" → profile v2 → **Find more like these** returns lookalikes.
7. Throughout: the Band web app sits next to First100, showing the agent team handing leads to each other in the room. In step 2, the founder redirects `@Scout` live. (Bonus) Insights shows cost per reply by industry, backed by Flexprice.

---

## 7. Bonus integrations

### Flexprice — what each lead costs us
Flexprice is a metering platform: you send usage events, meters add them up, and it reports usage per customer. We use it to answer **"how much have we spent finding these leads, and what did it buy us?"**

**What we meter:** every paid external call, tagged with the lead it was for.

| Event name | Fired when | Properties |
|---|---|---|
| `llm.call` | any Ollama call (token counts from `prompt_eval_count` / `eval_count`) | `lead_id?`, `agent`, `input_tokens`, `output_tokens`, `cost_usd` |
| `search.call` | Tavily search | `lead_id?`, `agent`, `cost_usd` |
| `contact.lookup` | Hunter domain-search / email-verifier | `lead_id`, `kind`, `cost_usd` |
| `email.sent` | send (simulated or real) | `lead_id`, `cost_usd` (0 when simulated) |

`cost_usd` is computed locally from unit prices in `app/usage.py`: a token rate for the local model (0 unless you want to show a notional cost), per-call rates for Tavily and Hunter. Fill these in from the plans you're actually on. Calls made before a lead exists (intake, segment inference, discovery queries) have no `lead_id` and count as run overhead.

**Wired in from H0, sent to Flexprice last:**
- **H0:** the cache wrapper every external call already goes through also calls `track(event)` in `app/usage.py`. That writes a row to a local `usage` table. Every agent is metered from the start at no extra cost, and replays from cache record `cost_usd = 0` (marked `cached: true`).
- **Last (H9–10):** `app/connectors/flexprice.py`, a background task started in `main.py`, sends unsent `usage` rows to Flexprice in batches (`POST /v1/events/bulk`) every few seconds, marking them `synced`. One customer per founder (`external_customer_id = founder.id`). A meter in Flexprice sums `cost_usd` and counts each event type. If `FLEXPRICE_API_KEY` is missing, nothing is sent and the local numbers still show.

**What the founder sees** (read from the local `usage` table so the UI works before Flexprice is connected; switch to Flexprice's usage API at the end if time allows):
- **Lead drawer:** "Cost to find this lead: $0.14" broken down by research, contact lookup and writing.
- **Insights:** total spent, cost per lead, **cost per reply** and **cost per meeting**, also split by industry. This links cost to the learning loop: "Logistics leads cost $0.11 each and reply 3× more often."
- **Header chip:** "Spent so far: $4.82 on 37 leads."

**Effort:** the `track()` hook is ~20 min at H0. The Flexprice sync, meter setup and UI numbers are ~1 h, built last.

### Band — the agents' handoff bus (core, not optional)
Band is a platform + desktop app where agents and humans work together in shared **rooms**. **First100 uses Band's mention-routed messaging as the real handoff mechanism between agents**: there is no in-process chain behind it. Key mechanics (from [docs.band.ai](https://docs.band.ai/getting-started/connect-remote-agent)):
- Each agent is a separate identity (ID + API key from **Agents → Connect remote agent**). Our code is the runtime; Band only routes messages.
- **Agents act only when @mentioned.** Mentions are how agents hand work to each other.
- Humans in the room see everything: messages, the agents' reasoning, tool calls, errors.
- Use the Band **web app** (not Band Desktop, which is for running coding agents like Claude Code). Agents are created under **Agents → Connect remote agent**.
- Python SDK: `band-sdk==6.0.1`. Start with `Agent.from_config("scout", adapter=adapter)` and `await agent.run()`; reply with `band_send_message`.

**Design: the sales team in a room.** One room per founder, "First100 — {product}", with the founder plus 5 agents (§3). **Routing is LLM-driven and defined in the prompts**: each agent's prompt says who it hands to and when, and the agent's LLM picks who to @mention. The intended flow:

| Band agent | Typical trigger | Hands off to (per its prompt) |
|---|---|---|
| **Team** (coordinator) | founder talks to the team ("@Team find leads") or web app asks | whichever teammate fits, e.g. `@Scout` for a new search |
| **Scout** | asked for a search; founder gives a rule | `@Researcher` once per company found; confirms rules to the founder |
| **Researcher** | handed a company; founder correction | Tier A/B → `@Writer`; Tier C → drops it, tells whoever asked why; redo after a draft → asks `@Writer` to redraft |
| **Writer** | handed a researched lead; founder decision | draft ready → `@founder` to check and approve; thin evidence → `@Researcher` |
| **Learner** | founder asks what's working | proposal → `@founder`; on accept → `@Scout` to search again |

**Redo on request.** The founder can correct any agent in plain words ("@Researcher that's the wrong Acme, look again"). The agent's LLM calls the same tool with the correction (`research_lead(correction=…)`, `draft_outreach(feedback=…)`). Inside the tool: the lead's `stage` goes back, old evidence is marked rejected and its URLs are excluded. If downstream work exists (a draft), the prompt tells the agent to ask that teammate to redo it.

**Messages.** Written by each agent's LLM for the founder to read: what was found or done, then what's needed. Every handoff names the company and lead id ("Acme Freight, lead 3"); the next agent loads the full record with `get_lead`. Lead data stays in SQLite/Neo4j; raw page text and JSON never go in chat. Tool calls and results show in the room as events (`Emit.TOOL_CALLS`), so the founder sees the work, not just the summary.

Example of the room during a run:
> **Founder:** @Team hey, find me some leads.
> **Team:** @Scout the founder wants a new search for leads on the current profile.
> **Scout:** Found Acme Freight (lead 1), which just announced a new Dallas warehouse. Can you research it?  *(mentions Researcher)*
> **Researcher:** Acme Freight (lead 1) checks out: a second Dallas warehouse and 2 inventory-manager openings. Tier A, 87; best contact Jane Doe, COO, and you both worked at Stripe. Can you draft the outreach?  *(mentions Writer)*
> **Writer:** I've pushed the draft for Jane Doe at Acme Freight to the approval queue, please check and approve.  *(mentions the founder)*
> **Researcher:** Dropped Boxly Logistics (lead 2): the only source was a 2023 press release.
> **Founder:** @Researcher the Acme signal is about a different Acme, can you look it up again?

**Implementation:**
- `app/band/bridge.py`: every agent in `agents/team.py` runs on `OllamaAdapter` (`app/band/ollama_adapter.py`), a small Band adapter for a local Ollama model. Band ships no Ollama adapter, so it converts room history to Ollama chat messages, offers Band's tools plus the agent's own on each call, and runs the tool loop itself. Config: `custom_section` = the agent's prompt (Band adds the agent's identity from its Band description; its base instructions are left out, `shared.md` covers how the room works), `additional_tools` = the agent's tools, recent history only (`max_history_messages=40`). Band's peer-discovery tools (`band_lookup_peers`, `band_add_participant`, …) are excluded: the team is fixed. Started as asyncio tasks in FastAPI's startup; standalone: `python -m app.band.bridge`.
- **Find leads** in the web app → API → `Team` agent posts to `@Scout`. So every run starts visibly in the room.
- Founder actions in Band ("approve", "skip under 50 people", "look again") and in the web app call the same code (tools and API routes share functions). Approving in either place updates both; when the founder acts in the web app, the relevant agent posts a one-line note in the room so the room's story stays complete.
- Every Band message an agent sends is also `emit()`ed, so the in-app activity panel mirrors the room.
- **Watchdog:** a background task checks leads whose `stage` hasn't changed for ~60s and nudges the agent that should act next, so a missed or mis-routed handoff doesn't silently stall a lead.
- **Every turn ends with a message or `band_no_reply`** (the team prompt tells agents to use `band_no_reply` when a teammate is only reporting). Otherwise Band marks the turn failed.
- **One room, no session isolation (for now).** The demo uses one founder in one room, so data isn't scoped by `room_id`. If a second room is ever needed: add a `rooms (room_id, founder_id)` table, a `founder_id` on leads/profiles/drafts/outcomes, and scope lead lookups by room.

**Cost per turn.** A typical turn is ~3 model calls (call a tool, send the message, finish). A run with N leads is roughly 4 + 7N calls, all on the local model, so speed is the limit; cap discovery batch size for the demo.

**Demo moment:** the Band web app next to First100. Click **Find leads** and the room fills with agents handing work to each other. Then correct an agent live (`@Researcher that's the wrong Acme, look again` or `@Scout skip under 50 people`) and watch it redo the work and hand it on.

**Checks:**
1. ✅ Agents connect and reply to mentions.
2. ✅ An agent's @mention of another agent wakes it.
3. Check Band's message rate limits: ~8 leads × 3–4 hops ≈ 30 messages per run.
4. Check the Sample Project page in the Band docs to see whether approvals can be native Band actions instead of chat replies.

---

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Tavily returns stale or irrelevant pages | Add date/recency terms to queries; Scorer weights recency; cache good runs |
| LLM invents citations | Substring-verify quotes; story validator rejects unknown `[n]` |
| Hunter finds no contact / runs out of credits | Show "No email found — try LinkedIn"; cache; free tier is small, so only enrich Tier A/B |
| Warm paths empty on stage | Seeded founder background chosen to overlap with real discovered leads; verify at H7 |
| Learning loop has no clear winner | Biased reply simulator |
| Live API failure during demo | Cache replay mode (`DEMO_MODE=cache`) + backup video |
| Band down or slow during demo | Pipeline depends on it, so: verify Band status before going on stage; backup video recorded early (not at H10) |
| A handoff is missed or the LLM mentions the wrong teammate | Routing rules spelled out in each prompt; watchdog nudges leads stuck in a stage > ~60s |
| Agents chat back and forth (thank-yous, relays) | Team prompt: no acknowledgements, `band_no_reply` when only informed; `max_tool_rounds` caps a turn |
| LLM skips a guardrail | Guardrails live inside tools (quote check, validators), not in prompts |
| A local 7B model is slow or picks the wrong tool on a busy run | Recent history only, cache inside tools, cap discovery batch size; switch `OLLAMA_MODEL` to a larger model if needed |
| Band rate limits on a busy run | Cap discovery batch size; check limits at H0 |

---

## 9. Env & setup checklist

```
# .env (repo root, read by app/config.py)
OLLAMA_URL=http://localhost:11434   # `ollama serve`
OLLAMA_MODEL=qwen2.5:7b
TAVILY_API_KEY=
HUNTER_API_KEY=
NEO4J_URI= / NEO4J_USER= / NEO4J_PASSWORD=
FLEXPRICE_API_KEY=        # optional; without it, cost tracking stays local
DEMO_MODE=live|cache
# Band: app/band/agent_config.yaml (gitignored), one entry per agent:
#   team / scout / researcher / writer / learner → { agent_id, api_key }
#   All 5 agents + the founder in one room.

# webapp/.env
VITE_API_URL=http://localhost:8000
```

Run locally:
```
python -m venv .venv && source .venv/bin/activate && pip install -r app/requirements.txt
uvicorn app.main:app --reload          # backend, from repo root
cd webapp && npm install && npm run dev  # frontend
```

Before the clock starts: create all accounts, confirm Hunter + Tavily free quotas, spin up Neo4j Aura, create the 5 Band agents and add them to the room, note your Band handle, pick the demo founder and sanity-check a few Tavily queries for their industry.
