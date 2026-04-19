"""Server-Sent Events endpoint for live UI updates.

The live_events queue is populated by the worker pool's on_progress callback.
Frontend clients subscribe to /api/stream and receive events as tickets move
through triage → resolve → complete.
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Global queue — worker pool pushes here; SSE clients drain it
_event_queue: asyncio.Queue[dict] = asyncio.Queue()


def push_event(ticket_id: str, payload: dict) -> None:
    """Called by worker_pool on_progress to broadcast an event."""
    event = {
        "type": payload.get("stage", "update"),
        "ticket_id": ticket_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    try:
        _event_queue.put_nowait(event)
    except asyncio.QueueFull:
        logger.warning("SSE event queue full, dropping event for %s", ticket_id)


async def _event_generator():
    """Async generator that yields SSE events from the queue."""
    while True:
        try:
            event = await asyncio.wait_for(_event_queue.get(), timeout=30.0)
            yield {"data": json.dumps(event, default=str)}
        except asyncio.TimeoutError:
            # Heartbeat to keep connection alive
            yield {"data": json.dumps({"type": "heartbeat", "timestamp": datetime.now(timezone.utc).isoformat()})}
        except asyncio.CancelledError:
            break


@router.get("/stream")
async def stream_events():
    """SSE endpoint — subscribe to receive real-time ticket processing events."""
    return EventSourceResponse(_event_generator())
