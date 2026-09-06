"""Post-debate ratings, and the profile aggregates built from them.

Three rules, each of which the schema already half-enforces:

* **Only a participant may rate**, guarded by ``to_room_read()`` — the same check chat and
  the fact-check use, so the four cannot drift apart about who was in a debate.
* **Only a finished debate may be rated.** Rating mid-argument would measure the argument's
  temperature, not the debate.
* **One rating per reviewer per room**, enforced by a database constraint and translated
  here. A second attempt is refused rather than silently overwriting the first — an
  overwrite would let someone revise a score after seeing the reply, and would quietly
  destroy the original.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.debate_room import DebateRoom
from app.models.user import User
from app.repositories import match as match_repo
from app.repositories import rating as rating_repo
from app.schemas.rating import (
    DebateHistoryEntry,
    RatingRead,
    RatingState,
    UserProfileRead,
)
from app.schemas.user import UserSummary
from app.services.match import to_room_read

logger = logging.getLogger(__name__)


def _opponent_of(room: DebateRoom, user_id: uuid.UUID) -> User:
    """The other debater. ``to_room_read`` has already proven the caller is one of the two."""
    return room.user2 if room.user1_id == user_id else room.user1


async def _get_room_for_participant(db: AsyncSession, room_id: uuid.UUID, user: User):
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    # Raises PermissionDeniedError for outsiders, before anything is read or written.
    to_room_read(room, user.id)
    return room


async def get_state(db: AsyncSession, room_id: uuid.UUID, user: User) -> RatingState:
    """Whether the caller has already rated this debate.

    The results screen asks before rendering the form, so a second visit shows what was
    submitted rather than an empty form that will be refused.
    """
    await _get_room_for_participant(db, room_id, user)
    existing = await rating_repo.get_rating_by_reviewer(db, room_id, user.id)
    if existing is None:
        return RatingState(submitted=False)
    return RatingState(submitted=True, rating=RatingRead.model_validate(existing))


async def submit(
    db: AsyncSession,
    room_id: uuid.UUID,
    user: User,
    *,
    score: int,
    comment: str | None,
) -> RatingRead:
    """Record one rating of the caller's opponent."""
    room = await _get_room_for_participant(db, room_id, user)
    if room.ended_at is None:
        raise ConflictError("This debate has not finished yet.")

    opponent = _opponent_of(room, user.id)

    try:
        rating = await rating_repo.add_rating(
            db,
            room_id=room_id,
            reviewer_id=user.id,
            reviewed_user_id=opponent.id,
            score=score,
            comment=comment,
        )
        await db.commit()
    except IntegrityError:
        # The unique constraint fired: they have already rated this debate. Checking first
        # would have been a longer race than the insert itself.
        await db.rollback()
        raise ConflictError("You have already rated this debate.") from None

    await db.refresh(rating)
    logger.info(
        "Rating recorded",
        extra={"room_id": str(room_id), "score": score},
    )
    return RatingRead.model_validate(rating)


async def get_profile(db: AsyncSession, user: User) -> UserProfileRead:
    """The caller's profile: their finished debates and the ratings they received.

    Deliberately the caller's own profile only. Public profiles would expose who debated
    whom, and the MVP has no privacy controls to make that a considered choice.
    """
    rooms = await rating_repo.finished_rooms_for(db, user.id)
    scores = await rating_repo.ratings_received_in_rooms(db, user.id, [room.id for room in rooms])

    history = [
        DebateHistoryEntry(
            id=room.id,
            topic_title=room.topic.title,
            opponent=UserSummary.model_validate(_opponent_of(room, user.id)),
            rating_received=scores.get(room.id),
            # `ended_at` is not null here — `finished_rooms_for` filters on it.
            date=room.ended_at,  # type: ignore[arg-type]
        )
        for room in rooms
    ]

    return UserProfileRead(
        user=UserSummary.model_validate(user),
        joined_at=user.created_at,
        debates_count=len(rooms),
        average_rating=await rating_repo.average_score_for(db, user.id),
        history=history,
    )
