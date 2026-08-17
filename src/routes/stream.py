"""SSE stream endpoint."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from src.bus import event_bus
from src.config import settings
from src.db import get_session
from src.errors import SessionNotFoundError
from src.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["stream"])


@router.get("/sessions/{session_id}/stream")
async def stream_events(
    session_id: str,
) -> EventSourceResponse:
    session = get_session(settings.db_path, session_id)
    if not session:
        raise SessionNotFoundError(f"Session {session_id} not found")

    async def event_generator():
        queue = event_bus.subscribe(session_id)
        try:
            # Send initial connection event
            yield {
                "event": "connected",
                "data": json.dumps({"session_id": session_id, "status": "connected"}),
            }
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield {
                        "event": event.get("event_type", "event"),
                        "data": json.dumps(event),
                    }
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield {"event": "heartbeat", "data": "{}"}
        except asyncio.CancelledError:
            pass
        finally:
            event_bus.unsubscribe(session_id, queue)
            logger.info("sse_client_disconnected", session_id=session_id)

    return EventSourceResponse(event_generator())
