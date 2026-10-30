"""One cache for every external call (Ollama, Tavily, Hunter).

Responses are stored as JSON files keyed by a hash of the full request, so a
changed prompt is a new key. With DEMO_MODE=cache, a miss is an error instead
of a network call, so the demo replays exactly what was recorded.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Awaitable, Callable

from app import config


class CacheMiss(RuntimeError):
    pass


async def cached(namespace: str, request: dict[str, Any], fetch: Callable[[], Awaitable[Any]]) -> Any:
    key = hashlib.sha256(json.dumps([namespace, request], sort_keys=True, default=str).encode()).hexdigest()[:24]
    path = config.CACHE_DIR / f"{namespace}-{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    if config.DEMO_MODE == "cache":
        raise CacheMiss(f"{namespace} request not in cache (DEMO_MODE=cache)")
    result = await fetch()
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, default=str))
    return result
