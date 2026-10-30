"""What the process costs: one usage row per live LLM call (PLAN.md §7).

The model runs locally, so the per-token rates are notional (what a hosted model of
the same size would charge); set LLM_COST_PER_1M_INPUT / _OUTPUT in .env to change them.
Cache replays never reach the model, so they cost nothing and aren't recorded.
"""

from __future__ import annotations

import json

from app import config, db


def llm_cost(input_tokens: int, output_tokens: int) -> float:
    return (input_tokens * config.LLM_COST_PER_1M_INPUT + output_tokens * config.LLM_COST_PER_1M_OUTPUT) / 1_000_000


def track_llm(ollama_response: dict, *, agent: str, lead_id: int | None = None) -> None:
    """Record one Ollama response; its token counts are `prompt_eval_count` and `eval_count`."""
    input_tokens = ollama_response.get("prompt_eval_count") or 0
    output_tokens = ollama_response.get("eval_count") or 0
    with db.connect() as c:
        c.execute(
            "INSERT INTO usage (event_name, lead_id, agent, props_json, cost_usd) VALUES ('llm.call', ?, ?, ?, ?)",
            (lead_id, agent, json.dumps({"input_tokens": input_tokens, "output_tokens": output_tokens}),
             llm_cost(input_tokens, output_tokens)),
        )
