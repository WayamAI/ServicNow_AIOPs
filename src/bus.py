"""In-process pub/sub event bus for SSE delivery."""

from __future__ import annotations

import asyncio
import threading
from collections import defaultdict

from src.logger import get_logger

logger = get_logger(__name__)


class EventBus:
    """Pub/sub for routing agent events to SSE clients.

    Subscribers receive events for a specific session via asyncio.Queue.
    Events are filtered by type if permissions are set.
    """

    def __init__(self) -> None:
        # session_id -> list of subscriber queues
        self._subscribers: dict[str, list[asyncio.Queue[dict]]] = defaultdict(list)
        # session_id -> set of allowed event types (None = all allowed)
        self._permissions: dict[str, set[str] | None] = {}
        # event loop reference for thread-safe publishing
        self._loop: asyncio.AbstractEventLoop | None = None
        # lock for mutations to _subscribers
        self._lock = threading.Lock()

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Set the event loop to use for thread-safe publishing."""
        self._loop = loop

    def subscribe(self, session_id: str) -> asyncio.Queue[dict]:
        """Create and register a new subscriber queue for a session."""
        queue: asyncio.Queue[dict] = asyncio.Queue()
        with self._lock:
            self._subscribers[session_id].append(queue)
        logger.info(
            "sse_subscriber_added",
            session_id=session_id,
            subscriber_count=len(self._subscribers[session_id]),
        )
        return queue

    def unsubscribe(self, session_id: str, queue: asyncio.Queue[dict]) -> None:
        """Remove a subscriber queue (SSE client disconnected)."""
        with self._lock:
            if session_id in self._subscribers:
                try:
                    self._subscribers[session_id].remove(queue)
                    logger.info("sse_subscriber_removed", session_id=session_id)
                except ValueError:
                    pass

    def publish(self, session_id: str, event: dict) -> None:
        """Publish an event to all subscribers of a session.

        Applies permission filtering. Drops event if no subscribers.
        Non-blocking — uses put_nowait. Thread-safe via call_soon_threadsafe.
        """
        event_type = event.get("event_type", "")
        allowed = self._permissions.get(session_id)
        if allowed is not None and event_type not in allowed:
            return

        subscribers = list(
            self._subscribers.get(session_id, [])
        )  # copy for thread safety
        if not subscribers:
            return

        for queue in subscribers:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(queue.put_nowait, event)
            else:
                try:
                    queue.put_nowait(event)
                except Exception:
                    pass

    def set_permissions(self, session_id: str, allowed_types: set[str]) -> None:
        """Gate which event types are forwarded to this session's subscribers."""
        self._permissions[session_id] = allowed_types

    def clear_permissions(self, session_id: str) -> None:
        """Remove permission gate — all event types allowed."""
        self._permissions.pop(session_id, None)

    def subscriber_count(self, session_id: str) -> int:
        """Return number of active subscribers for a session."""
        return len(self._subscribers.get(session_id, []))


# Global singleton
event_bus = EventBus()
