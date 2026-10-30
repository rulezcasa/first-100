"""Structured calls to a local Ollama model: a prompt in, a validated Pydantic model out."""

from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app import config
from app.connectors.cache import cached

T = TypeVar("T", bound=BaseModel)


def _inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic nests models via $defs/$ref; give Ollama one flat schema instead.

    Every property is also marked required: Ollama lets the model omit optional fields,
    and an omitted field comes back as its default (empty), silently wiping it.
    """
    defs = schema.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(defs[node["$ref"].split("/")[-1]])
            out = {k: walk(v) for k, v in node.items()}
            if out.get("type") == "object" and "properties" in out:
                out["required"] = list(out["properties"])
            return out
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


async def generate(
    prompt: str, schema: type[T], *, system: str = "", history: list[dict] | None = None, variant: int = 0,
) -> T:
    """One structured call, constrained to `schema`, with one retry on bad output.

    `history` is earlier chat turns as Ollama messages ({"role": "user" | "assistant", "content": ...}),
    sent before `prompt` so the model sees a real conversation rather than a pasted transcript.
    A new `variant` asks for a different answer to the same prompt: it is a fresh cache key and sampling seed.
    """
    history = history or []
    json_schema = _inline_refs(schema.model_json_schema())
    # Ollama constrains the output to the schema; showing it in the prompt too helps small models fill it well.
    full_system = f"{system}\n\nRespond with JSON matching this schema:\n{json.dumps(json_schema)}".strip()
    request = {"model": config.OLLAMA_MODEL, "system": full_system, "history": history, "prompt": prompt, "schema": json_schema}
    if variant:
        request["variant"] = variant  # absent by default, so existing cache entries still match

    async def fetch() -> str:
        async with httpx.AsyncClient(base_url=config.OLLAMA_URL, timeout=120) as http:
            response = await http.post("/api/chat", json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": full_system},
                    *history,
                    {"role": "user", "content": prompt},
                ],
                "format": json_schema,
                "stream": False,
                "options": {"temperature": 0.3, **({"seed": variant} if variant else {})},
            })
            response.raise_for_status()
            return response.json()["message"]["content"]

    for attempt in range(2):
        text = await cached("ollama", {**request, "attempt": attempt}, fetch)
        try:
            return schema.model_validate_json(text)
        except ValidationError:
            if attempt:
                raise
    raise AssertionError("unreachable")
