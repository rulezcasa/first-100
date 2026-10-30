"""API routes for the activity panel: the Band room, read and written as the founder."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.band import room

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("")
async def recent() -> list[dict]:
    try:
        return await room.recent()
    except room.RoomNotSet as e:
        raise HTTPException(503, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"Couldn't read the Band room: {e}") from e


class SendIn(BaseModel):
    text: str


@router.post("")
async def send(body: SendIn) -> dict:
    """Post to the room as the founder; agents reply in the room, and the stream carries it back."""
    text = body.text.strip()
    if not text:
        raise HTTPException(400, "Write something first.")
    try:
        return await room.send(text)
    except room.RoomNotSet as e:
        raise HTTPException(503, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    except Exception as e:
        raise HTTPException(502, f"Couldn't post to the Band room: {e}") from e


@router.get("/stream")
async def stream(request: Request) -> EventSourceResponse:
    """New room messages as server-sent events, one JSON RoomEvent each."""
    q = room.listen()

    async def events():
        try:
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(q.get(), timeout=15)
                except asyncio.TimeoutError:
                    continue  # sse-starlette sends keep-alive pings on its own
                yield {"event": "message", "data": json.dumps(event)}
        finally:
            room.stop_listening(q)

    return EventSourceResponse(events())
