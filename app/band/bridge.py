"""Connects every agent in agents/team.py to Band, one identity each.

Each agent runs on OllamaAdapter (ollama_adapter.py): when it's @mentioned, the
local model reads the room, calls the agent's tools as it sees fit, and replies or hands off by
@mentioning a teammate through band_send_message.

Run on its own (until main.py starts it):  python -m app.band.bridge
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import yaml
from band import Agent, configure_logging

from app.agents.team import AGENTS, AgentSpec
from app.band.ollama_adapter import OllamaAdapter

log = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent / "agent_config.yaml"

# The team is fixed, so agents don't get Band's tools for finding or adding other agents.
EXCLUDED_BAND_TOOLS = [
    "band_lookup_peers",
    "band_add_participant",
    "band_remove_participant",
    "band_create_chatroom",
]


def build_agent(name: str, spec: AgentSpec) -> Agent:
    adapter = OllamaAdapter(
        custom_section=spec.prompt,
        additional_tools=spec.tools,
        max_history_messages=40,  # recent room context only, so turns stay quick on a local model
        exclude_tools=EXCLUDED_BAND_TOOLS,
        may_not_mention=spec.may_not_mention,
    )
    return Agent.from_config(name, adapter=adapter, config_path=CONFIG_PATH)


async def run_all() -> None:
    configured = set(yaml.safe_load(CONFIG_PATH.read_text()) or {})
    agents = [build_agent(name, spec) for name, spec in AGENTS.items() if name in configured]
    if missing := set(AGENTS) - configured:
        log.warning("Not in agent_config.yaml, not started: %s", ", ".join(sorted(missing)))
    await asyncio.gather(*(a.run(install_signal_handlers=False) for a in agents))


if __name__ == "__main__":
    configure_logging()
    asyncio.run(run_all())
