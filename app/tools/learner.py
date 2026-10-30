"""Learner's tools: what's working, and updating who we target."""

from typing import Annotated

from pydantic import Field

from app.tools import stub_data


def _rate(counts: dict) -> float:
    return round(counts["replied"] / counts["sent"], 2) if counts["sent"] else 0.0


async def analyze_outcomes() -> dict:
    """Reply rates so far by industry and by email angle (signal vs pain), with counts."""
    # TODO: read outcomes from the database
    return {
        dimension: {key: {**counts, "reply_rate": _rate(counts)} for key, counts in groups.items()}
        for dimension, groups in stub_data.OUTCOMES.items()
    }


async def update_profile(
    change: Annotated[str, Field(description="What changes, in one line, e.g. 'focus on logistics, use signal emails'")],
) -> dict:
    """Update the target profile to a new version with a one-line change note. The next search uses it."""
    stub_data.PROFILE["version"] += 1
    stub_data.PROFILE["change_note"] = change
    return {"version": stub_data.PROFILE["version"], "change_note": change}
