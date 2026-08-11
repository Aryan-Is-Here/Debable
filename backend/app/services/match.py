"""Matchmaking rules.

The flow, in one place:

* ``join`` puts the caller in a topic's queue, unless someone is already waiting there — in
  which case it takes that person out of the queue and opens a room for the two of them.
* The user who was already waiting learns about it on their next ``get_state`` poll, which
  finds the open room they are a participant of.
* ``leave`` withdraws from the queue.

Correctness under concurrency lives in the repository's ``claim_waiting_opponent``, which
locks its candidate with ``FOR UPDATE SKIP LOCKED`` so two simultaneous joins cannot both
claim the same person.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models.debate_room import DebateRoom
from app.models.topic import TopicStatus
from app.models.user import User
from app.repositories import match as match_repo
from app.repositories import topic as topic_repo
from app.schemas.match import DebateRoomRead, MatchState, MatchStatus
from app.schemas.topic import TopicRead
from app.schemas.user import UserSummary

logger = logging.getLogger(__name__)


def to_room_read(room: DebateRoom, viewer_id: uuid.UUID) -> DebateRoomRead:
    """Render a room from one participant's point of view."""
    if viewer_id == room.user1_id:
        you, opponent = room.user1, room.user2
    elif viewer_id == room.user2_id:
        you, opponent = room.user2, room.user1
    else:
        # Rooms are private to their two debaters; there is no spectator mode in the MVP.
        raise PermissionDeniedError("You are not a participant in this debate.")

    return DebateRoomRead(
        id=room.id,
        topic=TopicRead.model_validate(room.topic),
        you=UserSummary.model_validate(you),
        opponent=UserSummary.model_validate(opponent),
        started_at=room.started_at,
        ended_at=room.ended_at,
    )


async def get_state(db: AsyncSession, user: User) -> MatchState:
    """What the caller is currently doing: idle, queued, or matched."""
    room = await match_repo.get_active_room_for_user(db, user.id)
    if room is not None:
        return MatchState(status=MatchStatus.MATCHED, room=to_room_read(room, user.id))

    entry = await match_repo.get_queue_entry(db, user.id)
    if entry is None:
        return MatchState(status=MatchStatus.IDLE)

    counts = await match_repo.waiting_counts(db, [entry.topic_id])
    return MatchState(
        status=MatchStatus.QUEUED,
        topic=TopicRead.model_validate(entry.topic),
        queued_at=entry.created_at,
        waiting_count=counts.get(entry.topic_id, 1),
    )


async def join(db: AsyncSession, user: User, topic_id: uuid.UUID) -> MatchState:
    """Queue for a topic, pairing immediately if someone is already waiting."""
    topic = await topic_repo.get_topic(db, topic_id)
    if topic is None:
        raise NotFoundError("Topic not found.")
    if topic.status == TopicStatus.ARCHIVED:
        raise ConflictError("This topic is archived and no longer accepts debates.")

    # Already debating? Send them back to that room rather than opening a second one.
    existing_room = await match_repo.get_active_room_for_user(db, user.id)
    if existing_room is not None:
        return MatchState(status=MatchStatus.MATCHED, room=to_room_read(existing_room, user.id))

    opponent_entry = await match_repo.claim_waiting_opponent(db, topic_id=topic_id, user_id=user.id)

    if opponent_entry is None:
        # Nobody waiting — join the queue. Switching topics replaces the old entry, since a
        # user may only hold one place in the queue.
        await match_repo.dequeue(db, user.id)
        try:
            entry = await match_repo.enqueue(db, user_id=user.id, topic_id=topic_id)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ConflictError("You are already in the matchmaking queue.") from None

        counts = await match_repo.waiting_counts(db, [topic_id])
        return MatchState(
            status=MatchStatus.QUEUED,
            topic=TopicRead.model_validate(topic),
            queued_at=entry.created_at,
            waiting_count=counts.get(topic_id, 1),
        )

    opponent_id = opponent_entry.user_id
    await match_repo.dequeue_many(db, [user.id, opponent_id])
    room = await match_repo.create_room(
        db, topic_id=topic_id, user1_id=opponent_id, user2_id=user.id
    )
    await db.commit()

    logger.info(
        "Debate room opened",
        extra={"room_id": str(room.id), "topic_id": str(topic_id)},
    )
    return MatchState(status=MatchStatus.MATCHED, room=to_room_read(room, user.id))


async def leave(db: AsyncSession, user: User) -> MatchState:
    """Withdraw from the queue. Harmless if the caller was not queued."""
    removed = await match_repo.dequeue(db, user.id)
    await db.commit()
    if removed:
        logger.info("Left matchmaking queue", extra={"user_id": str(user.id)})
    return MatchState(status=MatchStatus.IDLE)


async def get_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> DebateRoomRead:
    """One room, visible only to its two participants."""
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    return to_room_read(room, user.id)


async def end_room(db: AsyncSession, room_id: uuid.UUID, user: User) -> DebateRoomRead:
    """End a debate. Either participant may do this, and doing it twice is harmless."""
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    # Raises if the caller is not a participant, before any mutation happens.
    to_room_read(room, user.id)

    await match_repo.end_room(db, room)
    await db.commit()
    return to_room_read(room, user.id)
