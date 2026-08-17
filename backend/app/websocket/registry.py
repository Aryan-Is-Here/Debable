"""Which sockets are currently listening to which debate room.

⚠️ **This registry is per-process and does not survive multiple workers.** Two debaters
served by different uvicorn workers would each be broadcast to an empty set and see none of
the other's messages. It is the same trap that ruled out an in-memory matchmaking queue in
Phase 4 — the difference is that a queue could be moved into Postgres, while a broadcast
needs a channel, so this is deferred rather than solved.

Deployment (Phase 9) must therefore either pin the API to a single worker or put a broker
(Redis pub/sub, or Postgres ``LISTEN``/``NOTIFY``) behind ``broadcast``. Persistence is
unaffected either way: messages are in the ``messages`` table before they are ever
broadcast, so the worst case is a message that needs a reload to appear, not one that is
lost.
"""

import asyncio
import logging
import uuid
from collections import defaultdict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionRegistry:
    """Room id → the open sockets watching it."""

    def __init__(self) -> None:
        self._rooms: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        # Membership changes and broadcasts interleave on one event loop, but a broadcast
        # awaits between sends; the lock keeps it from iterating a set that a disconnecting
        # socket is mutating underneath it.
        self._lock = asyncio.Lock()

    async def add(self, room_id: uuid.UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[room_id].add(websocket)

    async def discard(self, room_id: uuid.UUID, websocket: WebSocket) -> None:
        """Remove a socket. Safe to call twice — disconnect paths overlap."""
        async with self._lock:
            sockets = self._rooms.get(room_id)
            if sockets is None:
                return
            sockets.discard(websocket)
            # Drop the empty set so a long-running process does not accumulate one entry
            # per debate ever held.
            if not sockets:
                del self._rooms[room_id]

    async def connection_count(self, room_id: uuid.UUID) -> int:
        async with self._lock:
            return len(self._rooms.get(room_id, ()))

    async def broadcast(self, room_id: uuid.UUID, payload: dict) -> None:
        """Send ``payload`` to every socket in the room, including the original sender.

        A send that fails means that peer is gone — its own handler will clean up, and its
        connection must not fail the message for anyone else. So failures are collected and
        dropped rather than raised: the sender's message is already committed, and telling
        them it failed because their opponent's laptop closed would be a lie.
        """
        async with self._lock:
            targets = list(self._rooms.get(room_id, ()))

        dead: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001 - any send failure means the peer is gone
                dead.append(websocket)

        for websocket in dead:
            logger.info("Dropping a dead chat socket", extra={"room_id": str(room_id)})
            await self.discard(room_id, websocket)


# One registry per process, shared by every connection.
chat_registry = ConnectionRegistry()
