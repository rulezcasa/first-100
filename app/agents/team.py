"""The team: each agent is a prompt plus the tools it may use, keyed by its name in
app/band/agent_config.yaml.

The prompt (app/prompts/<name>.md) gives the agent its context and role; the LLM
decides which tools to call and who to @mention.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.prompts import agent_prompt
from app.tools import ToolDef, learner, researcher, scout, shared, tool, writer


# Learner isn't built yet (its tools still read stub data), so nobody hands work to it.
NO_LEARNER = {"learner": "Learner isn't set up yet, so don't involve it."}


@dataclass
class AgentSpec:
    prompt: str
    functions: list[Callable[..., Awaitable[Any]]] = field(default_factory=list)
    # Teammates this agent must not @mention, and why; enforced in OllamaAdapter, so the handoff order holds.
    may_not_mention: dict[str, str] = field(default_factory=lambda: dict(NO_LEARNER))

    @property
    def tools(self) -> list[ToolDef]:
        return [tool(fn) for fn in self.functions]


AGENTS: dict[str, AgentSpec] = {
    "team": AgentSpec(agent_prompt("team")),
    "scout": AgentSpec(agent_prompt("scout"), [
        scout.get_profile, scout.suggest_segments, scout.add_filter, scout.find_companies, scout.find_lookalikes, shared.list_leads,
    ], may_not_mention={**NO_LEARNER, "writer": "New leads go to Researcher, not Writer: Researcher checks them and "
                                                "hands the strong ones to Writer."}),
    "researcher": AgentSpec(agent_prompt("researcher"), [
        researcher.research_lead, researcher.skip_lead, shared.get_lead, shared.list_leads,
    ]),
    "writer": AgentSpec(agent_prompt("writer"), [
        writer.draft_outreach, writer.approve_draft, writer.reject_draft, shared.get_lead, shared.list_leads,
    ]),
    "learner": AgentSpec(agent_prompt("learner"), [
        learner.analyze_outcomes, learner.update_profile,
    ]),
}
