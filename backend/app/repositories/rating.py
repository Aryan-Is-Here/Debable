"""Rating persistence, plus the aggregates the profile screen needs.

The uniqueness rule is not re-checked here. ``ratings`` carries a
``UniqueConstraint(room_id, reviewer_id)``, so a "have they rated already?" query followed by
an insert would be a race with a longer window than the insert itself — two submissions
milliseconds apart would both read "no" and both proceed. The insert is allowed to fail and
the service translates it, which is the same shape ``match.join`` uses for the queue.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.debate_room import DebateRoom
from app.models.rating import Rating
from app.models.topic import Topic


async def add_rating(
    db: AsyncSession,
    *,
    room_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    reviewed_user_id: uuid.UUID,
    score: int,
    comment: str | None,
) -> Rating:
    """Insert a rating. Raises ``IntegrityError`` on a duplicate; the caller commits."""
    rating = Rating(
        room_id=room_id,
        reviewer_id=reviewer_id,
        reviewed_user_id=reviewed_user_id,
        score=score,
        comment=comment,
    )
    db.add(rating)
    await db.flush()
    return rating


async def get_rating_by_reviewer(
    db: AsyncSession, room_id: uuid.UUID, reviewer_id: uuid.UUID
) -> Rating | None:
    """The caller's own rating of a debate, if they left one."""
    return await db.scalar(
        select(Rating).where(Rating.room_id == room_id, Rating.reviewer_id == reviewer_id)
    )


async def average_score_for(db: AsyncSession, user_id: uuid.UUID) -> float | None:
    """Mean rating received. ``None`` when nobody has rated them yet."""
    average = await db.scalar(
        select(func.avg(Rating.score)).where(Rating.reviewed_user_id == user_id)
    )
    return float(average) if average is not None else None


async def finished_rooms_for(db: AsyncSession, user_id: uuid.UUID) -> Sequence[DebateRoom]:
    """A user's ended debates, newest first, with topic and both participants loaded.

    ``selectinload`` rather than lazy access: this feeds a list, and lazy loading here would
    issue a query per row — the pattern already established in ``app/repositories/match.py``.
    """
    result = await db.scalars(
        select(DebateRoom)
        .options(
            selectinload(DebateRoom.topic).selectinload(Topic.creator),
            selectinload(DebateRoom.user1),
            selectinload(DebateRoom.user2),
        )
        .where(
            (DebateRoom.user1_id == user_id) | (DebateRoom.user2_id == user_id),
            DebateRoom.ended_at.is_not(None),
        )
        .order_by(DebateRoom.ended_at.desc())
    )
    return result.all()


async def ratings_received_in_rooms(
    db: AsyncSession, user_id: uuid.UUID, room_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Scores this user received, keyed by room.

    One grouped query for the whole history rather than one per row — the same reasoning as
    the queue counts on the browse page.
    """
    if not room_ids:
        return {}
    rows = await db.execute(
        select(Rating.room_id, Rating.score).where(
            Rating.reviewed_user_id == user_id, Rating.room_id.in_(room_ids)
        )
    )
    return {room_id: score for room_id, score in rows.all()}
