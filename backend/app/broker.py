"""In-process async pub/sub broker for real-time SSE fan-out.

Replaces per-connection DB polling with an event-driven push: a write path publishes ONCE and every
subscribed SSE generator receives it immediately. DB load becomes O(writes) instead of
O(open_connections × poll_rate).

Scope & limits (documented in ARCHITECTURE.md §8): this broker is in-memory and therefore
single-process. Running multiple API workers requires swapping the transport for Redis Pub/Sub or
Postgres LISTEN/NOTIFY — the publish/subscribe interface here is intentionally the same shape so that
migration is a drop-in. Messages are best-effort: a slow subscriber whose queue fills simply drops
frames (the client reconnect + REST backfill reconciles), so one stuck consumer can never block a
writer or another consumer.

Publishing happens from sync request handlers (FastAPI runs them in a threadpool), while subscribers
live on the event loop; `publish()` therefore hops onto the loop via `call_soon_threadsafe`.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass


@dataclass
class Message:
    topic: str            # "activity" (broadcast) or "notify"
    data: dict
    target: int | None = None  # None = broadcast; else only subscribers for this user_id


class Broker:
    def __init__(self) -> None:
        self._subs: set[asyncio.Queue[Message]] = set()
        self._filters: dict[asyncio.Queue[Message], tuple[str, int | None]] = {}
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self, topic: str, user_id: int | None = None) -> asyncio.Queue[Message]:
        q: asyncio.Queue[Message] = asyncio.Queue(maxsize=200)
        self._subs.add(q)
        self._filters[q] = (topic, user_id)
        return q

    def unsubscribe(self, q: asyncio.Queue[Message]) -> None:
        self._subs.discard(q)
        self._filters.pop(q, None)

    @property
    def subscriber_count(self) -> int:
        return len(self._subs)

    def publish(self, topic: str, data: dict, target: int | None = None) -> None:
        """Fan a message out to matching subscribers. Safe to call from sync (threadpool) code."""
        loop = self._loop
        if loop is None:
            return  # no loop bound yet (e.g. during import or a non-async context) — drop silently
        msg = Message(topic=topic, data=data, target=target)

        def _fanout() -> None:
            for q, (sub_topic, sub_uid) in list(self._filters.items()):
                if sub_topic != topic:
                    continue
                if msg.target is not None and sub_uid != msg.target:
                    continue
                try:
                    q.put_nowait(msg)
                except asyncio.QueueFull:
                    pass  # slow consumer: drop; client reconnect + REST backfill reconciles

        try:
            loop.call_soon_threadsafe(_fanout)
        except RuntimeError:
            pass  # loop closed during shutdown


# Module-level singleton — imported by the write paths and the SSE endpoints.
broker = Broker()
