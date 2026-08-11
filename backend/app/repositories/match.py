"""Matchmaking queue and debate room persistence."""

import uuid
from collections.abc import Sequence
from datetime import timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.debate_room import DebateRoom
from app.models.match_queue import MatchQueueEntry
from app.models.topic import Topic

# How long a queue entry stays valid without a heartbeat. The waiting room polls every two
# seconds, so this is generous — it only has to outlast a slow network, not a closed tab.
QUEUE_STALE_AFTER = timedelta(seconds=30)


def _fresh_cutoff():
    """SQL expression for the oldest heartbeat still considered live."""
    return func.now() - QUEUE_STALE_AFTER


async def get_queue_entry(db: AsyncSession, user_id: uuid.UUID) -> MatchQueueEntry | None:
    """The caller's queue row, if they are waiting."""
    return await db.scalar(
        select(MatchQueueEntry)
        .options(selectinload(MatchQueueEntry.topic).selectinload(Topic.creator))
        .where(MatchQueueEntry.user_id == user_id)
    )


async def claim_waiting_opponent(
    db: AsyncSession, *, topic_id: uuid.UUID, user_id: uuid.UUID
) -> MatchQueueEntry | None:
    """Lock and return the longest-waiting other user on this topic, if any.

    ``FOR UPDATE SKIP LOCKED`` is what makes concurrent matching correct: the row is locked
    for this transaction, and any other request pairing at the same instant skips past it
    to the next candidate instead of blocking or — far worse — handing the same opponent to
    two people. The lock is released when the caller's transaction ends.
    """
    return await db.scalar(
        select(MatchQueueEntry)
        .where(
            MatchQueueEntry.topic_id == topic_id,
            MatchQueueEntry.user_id != user_id,
            # Never pair someone with a tab that stopped polling.
            MatchQueueEntry.last_seen_at >= _fresh_cutoff(),
        )
        .order_by(MatchQueueEntry.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )


async def touch(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Record that the caller is still waiting."""
    await db.execute(
        update(MatchQueueEntry)
        .where(MatchQueueEntry.user_id == user_id)
        .values(last_seen_at=func.now())
    )


async def sweep_stale(db: AsyncSession) -> int:
    """Delete entries that stopped heartbeating. Returns how many were removed.

    Called opportunistically from the matchmaking endpoints rather than from a background
    job: the queue is only interesting while someone is using it, and a cron for a handful
    of rows is machinery this does not need.
    """
    result = await db.execute(
        delete(MatchQueueEntry).where(MatchQueueEntry.last_seen_at < _fresh_cutoff())
    )
    return result.rowcount or 0


async def enqueue(db: AsyncSession, *, user_id: uuid.UUID, topic_id: uuid.UUID) -> MatchQueueEntry:
    """Add the user to a topic's queue."""
    entry = MatchQueueEntry(user_id=user_id, topic_id=topic_id)
    db.add(entry)
    await db.flush()
    await db.refresh(entry, attribute_names=["created_at"])
    return entry


async def dequeue(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Remove the user from the queue. Returns whether a row was actually removed."""
    result = await db.execute(delete(MatchQueueEntry).where(MatchQueueEntry.user_id == user_id))
    return bool(result.rowcount)


async def dequeue_many(db: AsyncSession, user_ids: Sequence[uuid.UUID]) -> None:
    await db.execute(delete(MatchQueueEntry).where(MatchQueueEntry.user_id.in_(user_ids)))


async def waiting_counts(db: AsyncSession, topic_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
    """How many people are queued per topic, for the ``activeDebaters`` field."""
    if not topic_ids:
        return {}
    rows = await db.execute(
        select(MatchQueueEntry.topic_id, func.count())
        .where(
            MatchQueueEntry.topic_id.in_(topic_ids),
            # Only count people actually still there.
            MatchQueueEntry.last_seen_at >= _fresh_cutoff(),
        )
        .group_by(MatchQueueEntry.topic_id)
    )
    return {topic_id: count for topic_id, count in rows.all()}


async def create_room(
    db: AsyncSession, *, topic_id: uuid.UUID, user1_id: uuid.UUID, user2_id: uuid.UUID
) -> DebateRoom:
    """Open a debate room between two users."""
    room = DebateRoom(topic_id=topic_id, user1_id=user1_id, user2_id=user2_id)
    db.add(room)
    await db.flush()
    return await get_room(db, room.id)  # type: ignore[return-value]


async def get_room(db: AsyncSession, room_id: uuid.UUID) -> DebateRoom | None:
    """A room with its topic and both participants loaded."""
    return await db.scalar(
        select(DebateRoom)
        .options(
            selectinload(DebateRoom.topic).selectinload(Topic.creator),
            selectinload(DebateRoom.user1),
            selectinload(DebateRoom.user2),
        )
        .where(DebateRoom.id == room_id)
    )


async def get_active_room_for_user(db: AsyncSession, user_id: uuid.UUID) -> DebateRoom | None:
    """The user's currently open room, if they are in one.

    This is how the waiting user learns they were matched: the other side created the room,
    and the next poll finds it here.
    """
    return await db.scalar(
        select(DebateRoom)
        .options(
            selectinload(DebateRoom.topic).selectinload(Topic.creator),
            selectinload(DebateRoom.user1),
            selectinload(DebateRoom.user2),
        )
        .where(
            DebateRoom.ended_at.is_(None),
            (DebateRoom.user1_id == user_id) | (DebateRoom.user2_id == user_id),
        )
        .order_by(DebateRoom.started_at.desc())
        .limit(1)
    )


async def end_room(db: AsyncSession, room: DebateRoom) -> DebateRoom:
    """Close a room. Idempotent — an already-ended room keeps its original end time."""
    if room.ended_at is None:
        room.ended_at = func.now()
        await db.flush()
        await db.refresh(room, attribute_names=["ended_at"])
    return room
