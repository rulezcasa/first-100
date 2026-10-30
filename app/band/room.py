"""The founder's side of the Band room (BAND_ROOM_ID), using the founder's own key (BAND_API_KEY).

The web app's activity panel is a view of this room: `send` posts there as the founder, so
the agents wake exactly as if the founder had typed in Band, and `watch` follows everything
said there and hands each new message to whoever is listening.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any

from band_rest import AsyncRestClient
from band_rest.types import ChatMessageRequest, ChatMessageRequestMentionsItem

from app import config

log = logging.getLogger(__name__)

# What the panel shows: what was said, which tools ran (and failed), and turn errors.
SHOWN_TYPES = ["text", "tool_call", "tool_result", "error"]
POLL_SECONDS = 1.5
DEFAULT_MENTION = "team"  # a message with no @mention goes to Team, the founder's front door

_client: AsyncRestClient | None = None
_listeners: set[asyncio.Queue] = set()


class RoomNotSet(RuntimeError):
    pass


def client() -> AsyncRestClient:
    global _client
    if not (config.BAND_API_KEY and config.BAND_ROOM_ID):
        raise RoomNotSet("Set BAND_API_KEY and BAND_ROOM_ID in .env to talk to the team.")
    if _client is None:
        _client = AsyncRestClient(api_key=config.BAND_API_KEY)
    return _client


def _readable(m: Any) -> str:
    """Band stores a mention as @[[participant id]]; show it as @Name."""
    text = m.content
    for mention in (m.metadata.model_dump().get("mentions") or []) if m.metadata else []:
        if mention.get("id") and mention.get("name"):
            text = text.replace(f"@[[{mention['id']}]]", f"@{mention['name']}")
    return text


def _event(m: Any) -> dict:
    """A Band message in the shape the panel draws (webapp/src/types.ts RoomEvent)."""
    event = {
        "id": m.id,
        "kind": m.message_type,
        "sender": m.sender_name or "",
        "from_founder": m.sender_type == "User",
        "text": _readable(m),
        "is_error": m.message_type == "error",
        "created_at": m.inserted_at.isoformat() if m.inserted_at else None,
    }
    if m.message_type in ("tool_call", "tool_result"):
        try:
            payload = json.loads(m.content)
        except ValueError:
            payload = {}
        event["text"] = payload.get("name", "")  # the tool's name; arguments and output stay out of the panel
        event["is_error"] = bool(payload.get("is_error"))
    return event


async def recent(limit: int = 60) -> list[dict]:
    """The latest messages, oldest first."""
    page = await client().human_api_messages.list_my_chat_messages(
        config.BAND_ROOM_ID, limit=limit, message_types=SHOWN_TYPES,
    )
    return [_event(m) for m in reversed(page.data)]


async def send(text: str) -> dict:
    """Post as the founder. Every @Name that matches someone in the room becomes a real mention."""
    people = (await client().human_api_participants.list_my_chat_participants(config.BAND_ROOM_ID)).data
    agents = [p for p in people if p.type == "Agent"]
    by_word = {w: p for p in agents for w in {(p.name or "").lower(), (p.handle or "").split("/")[-1].lower()} if w}
    mentioned = {}

    def to_token(match: re.Match) -> str:
        # Band's own mention syntax, so the platform doesn't add a second copy of the mention.
        p = by_word.get(match.group(1).lower())
        if p is None:
            return match.group(0)
        mentioned[p.id] = p
        return f"@[[{p.id}]]"

    text = re.sub(r"@([\w.-]+)", to_token, text)
    if not mentioned:
        team = next((p for p in agents if (p.name or "").lower() == DEFAULT_MENTION), None)
        if team is None:
            raise ValueError("Nobody to send this to: mention a teammate, e.g. @Scout.")
        mentioned[team.id] = team
        text = f"@[[{team.id}]] {text}"
    sent = await client().human_api_messages.send_my_chat_message(
        config.BAND_ROOM_ID,
        message=ChatMessageRequest(
            content=text,
            mentions=[ChatMessageRequestMentionsItem(id=p.id, handle=p.handle, name=p.name) for p in mentioned.values()],
        ),
    )
    return {"sent": True, "id": getattr(sent.data, "id", None)}


def listen() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _listeners.add(q)
    return q


def stop_listening(q: asyncio.Queue) -> None:
    _listeners.discard(q)


async def watch() -> None:
    """Poll the room and pass every new message to the listeners. Runs for the backend's lifetime."""
    since: datetime | None = None
    seen: set[str] = set()
    while True:
        try:
            page = await client().human_api_messages.list_my_chat_messages(
                config.BAND_ROOM_ID, limit=50, since=since, message_types=SHOWN_TYPES,
            )
            for m in reversed(page.data):  # oldest first
                if m.id in seen:
                    continue
                seen.add(m.id)
                if since is None:
                    continue  # the first poll only marks where "new" starts; the panel loads history itself
                for q in list(_listeners):
                    if not q.full():
                        q.put_nowait(_event(m))
            if page.data and page.data[0].inserted_at:
                since = page.data[0].inserted_at
            elif since is None:
                since = datetime.now().astimezone()
            if len(seen) > 2000:
                seen = {m.id for m in page.data}
        except asyncio.CancelledError:
            raise
        except Exception as e:  # Band unreachable for a moment: keep watching
            log.warning("Watching the Band room failed: %s", e)
        await asyncio.sleep(POLL_SECONDS)
