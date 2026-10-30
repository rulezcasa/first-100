"""The team: each agent is a prompt plus the tools it may use, keyed by its name in
app/band/agent_config.yaml.

The prompt (app/prompts/<name>.md) gives the agent its context and role; the LLM
decides which tools to call and who to @mention.
"""

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.prompts import agent_prompt
from app.tools import ToolDef, learner, researcher, scout, shared, tool, writer


@dataclass
class AgentSpec:
    prompt: str
    functions: list[Callable[..., Awaitable[Any]]] = field(default_factory=list)

    @property
    def tools(self) -> list[ToolDef]:
        return [tool(fn) for fn in self.functions]


AGENTS: dict[str, AgentSpec] = {
    "team": AgentSpec(agent_prompt("team")),
    "scout": AgentSpec(agent_prompt("scout"), [
        scout.get_profile, scout.suggest_segments, scout.add_filter, scout.find_companies, scout.find_lookalikes, shared.list_leads,
    ]),
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
