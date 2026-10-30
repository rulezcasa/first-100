"""Agent prompts as Markdown: shared.md is shared by every agent, <agent>.md adds its role."""

from pathlib import Path

DIR = Path(__file__).parent


def agent_prompt(name: str) -> str:
    """The full prompt for one agent: the shared team context, then its own role."""
    return (DIR / "shared.md").read_text() + "\n" + (DIR / f"{name}.md").read_text()
