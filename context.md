# First100 — Implementation Plan

This is for a one day hackathon, so its a minimal funcional protoype. Feel free to drop any prduction level architectural choices. 

> Niche pitch : **AI sales engine for founders doing their first 100 sales** but the product is general purposed.

---

## 1. The product

A founder with no sales team describes their product in plain words. First100 works out who should buy it, finds real companies and decision-makers on the public web, and explains **why each lead is a fit right now** with a short story where every claim links to a source. It drafts short, founder-voice outreach that the founder approves before anything is sent. As replies come in, it **learns which customer types and message angles work** and proposes updates to the target profile, which the founder accepts or rejects. Everything is tracked on one pipeline board.

---

## 2. The three differentiators

### D1. The cited "why now" story
Every lead shows a 2–4 sentence story explaining why this company and person, and why now. **Every sentence carries footnote references to evidence items**, each linking to a real fetched URL.

> *Acme Freight (Tier A, 87). They opened a second warehouse in Dallas three weeks ago [1], and are hiring two inventory managers [2]. Their COO, Jane Doe, previously ran operations at a company that adopted a similar tool [3].*


### D2. The learning loop
This really completes the loop by providing insights :

Track just two things per lead: industry and email angle (signal or pain, picked at random when drafting).

Outcomes: replied, no_reply, meeting.

Insights page: a table of reply rate by industry and by angle, with counts. Highlight the best and worst value. 

One proposal: "Focus on {best industry}" (and "use {best angle} emails"). Founder clicks Accept → the target profile moves to version 2 with a one-line note on what changed. The next discovery run uses it.

### D3. Built for founders doing their first 100 sales
This shapes the whole UX, not a single feature:
- **Plain language everywhere.** No jargon in the UI ("Who should buy this" not "ICP"; "Leads" not "Accounts"). Use a tooltip if a term is unavoidable.
- **Founder voice outreach.** Short (under 90 words), first person, one specific signal, one soft ask, no sales clichés. The founder's own story (from intake) is available as context.
- **Guided next step.** The dashboard always shows one clear "do this next" action.

---

 
## 3. Knowledge graph
 
### Nodes
`Founder`, `Company`, `Person`, `Signal`, `School`, `Investor`
 
### Relationships
```
(Person)-[:WORKS_AT]->(Company)
(Person)-[:PREVIOUSLY_WORKED_AT]->(Company)
(Person)-[:STUDIED_AT]->(School)
(Founder)-[:PREVIOUSLY_WORKED_AT]->(Company)
(Founder)-[:STUDIED_AT]->(School)
(Founder)-[:BACKED_BY]->(Investor)
(Company)-[:BACKED_BY]->(Investor)
(Company)-[:HAS_SIGNAL]->(Signal)        // Signal {type, summary, evidence_id}
(Founder)-[:CONTACTED]->(Person)
(Person)-[:REPLIED]->(Founder)
```
 
Match nodes on a normalized name (lowercase, strip "Inc", "LLC", etc.) using `MERGE`, so "Stripe" from the founder and "Stripe, Inc." from a web page become the same node.
 
### Where the data comes from
- **Founder** nodes and edges: the setup form.
- **Company, Person, WORKS_AT:** discovery + Hunter.
- **Signal:** each verified evidence item, tagged with a type (`funding`, `hiring`, `expansion`, `new_exec`, `product_launch`, `other`).
- **PREVIOUSLY_WORKED_AT, STUDIED_AT, Company BACKED_BY:** one extra Tavily search per Tier A/B lead (person name + company, and company + "investors"). The LLM extracts these **only** from fetched text; each edge stores its `evidence_id`. If nothing is found, create no edge.
- **CONTACTED / REPLIED:** written when emails are sent and replies are logged.
### The three queries (all in `lib/graph.ts`)
1. **`warmPaths(leadId)`** — any path of length ≤ 3 between the Founder and the lead's Person or Company through a shared Company, School, or Investor. Returns a readable explanation ("You both worked at Stripe").
2. **`lookalikes()`** — companies with the same `Signal` types as companies whose people `REPLIED`, not yet `CONTACTED`. Powers "Find more like these".
3. **`leadSubgraph(leadId)`** — the lead's company, person, signals, and any warm path, for the graph view.
### Graph view
In the lead drawer, a small force-directed graph of `leadSubgraph`: Founder → shared node → Person → Company → Signals. Warm path edges highlighted. This is the visual proof of the graph for judges.

## 4. Scope

### In scope
1. Product intake (chat + form) → structured profile
2. "Who should buy this" (ICP) inference with confidence scores and expansion suggestions
3. Lead discovery from public web search with citations
4. Lightweight competitor list
5. Knowledge graph (companies, people, signals, founder's network) with warm-path queries
6. Contact enrichment (email + verification status)
7. Outreach drafting (email sequence + LinkedIn note) with A/B variants
8. Human approval queue (approve / edit / reject)
9. Send (simulated by default, real optional)
10. Pipeline board with AI vs founder attribution
11. Learning loop: insights + ICP proposals + versioning
12. Basic analytics: funnel and conversion by segment and variant
13. Live "agent activity" panel

### Out of scope (do not build)
- Multi-user auth, teams, permissions
- Real LinkedIn sending (generate the note; founder copies it; mark as sent manually)
- Inbox syncing / real reply parsing (outcomes are logged manually or via the simulator)
- Payment flows, settings pages, mobile layouts, dark mode polish

---

### Additional integrations for bonus points (Plan and tell me how we can integrate this) :

1. Band Desktop (I think this will direcl)
2. Flexprice 