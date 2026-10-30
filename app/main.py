"""FastAPI app, plus the Band agents and the room watcher running alongside it.

Run: `fastapi dev main.py` from app/, or `uvicorn app.main:app --reload` from the repo root.
"""

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config, db
from app.api import activity, dashboard, drafts, leads, routes, who
from app.band import bridge, room
from app.connectors import flexprice

log = logging.getLogger(__name__)


def _report_crash(task: asyncio.Task) -> None:
    if not task.cancelled() and (e := task.exception()):
        log.error("%s stopped: %s", task.get_name(), e, exc_info=e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    tasks: list[asyncio.Task] = []
    if bridge.CONFIG_PATH.exists():
        tasks.append(asyncio.create_task(bridge.run_all(), name="Band agents"))
    else:
        log.warning("No %s, so the Band agents aren't started", bridge.CONFIG_PATH)
    if config.BAND_API_KEY and config.BAND_ROOM_ID:
        tasks.append(asyncio.create_task(room.watch(), name="Band room watcher"))
    else:
        log.warning("BAND_API_KEY or BAND_ROOM_ID not set, so the activity panel is offline")
    if flexprice.enabled():
        tasks.append(asyncio.create_task(flexprice.run(), name="Flexprice sync"))
    else:
        log.warning("FLEXPRICE_API_KEY not set, so costs stay local")
    for t in tasks:
        t.add_done_callback(_report_crash)
    yield
    for t in tasks:
        t.cancel()
    for t in tasks:
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await t


app = FastAPI(title="First100", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(routes.router)
app.include_router(who.router)
app.include_router(activity.router)
app.include_router(leads.router)
app.include_router(drafts.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
