"""Reporting a debater's conduct.

Almost identical to ``services/rating.py``, with one deliberate difference that matters:

**A report does not require the debate to have ended.** Ratings do, because rating
mid-argument measures the argument's temperature. Reporting is the opposite — harassment is
reported while it is happening, and telling someone to wait until the debate is over before
they can report it would be the wrong product entirely.

**A report is a record, not a workflow.** The MVP has no moderator (handbook §1 puts
moderation out of scope), so nothing here notifies, escalates or blocks. The endpoint's
response says so plainly rather than implying a review that will not happen.
"""

import logging
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.debate_room import DebateRoom
from app.models.user import User
from app.repositories import match as match_repo
from app.repositories import report as report_repo
from app.schemas.report import ReportRead
from app.services.match import to_room_read

logger = logging.getLogger(__name__)


def _opponent_of(room: DebateRoom, user_id: uuid.UUID) -> User:
    """The other debater. ``to_room_read`` has already proven the caller is one of the two."""
    return room.user2 if room.user1_id == user_id else room.user1


async def submit(
    db: AsyncSession,
    room_id: uuid.UUID,
    user: User,
    *,
    category: str,
    detail: str | None,
) -> ReportRead:
    """File one report against the caller's opponent."""
    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")
    # Raises PermissionDeniedError for outsiders. Being in the room is what makes someone a
    # witness — it is the whole basis for the report.
    to_room_read(room, user.id)

    opponent = _opponent_of(room, user.id)

    try:
        report = await report_repo.add_report(
            db,
            room_id=room_id,
            reporter_id=user.id,
            reported_user_id=opponent.id,
            category=category,
            detail=detail,
        )
        await db.commit()
    except IntegrityError:
        # The unique constraint fired. Not because a second report is harmful, but because
        # the same complaint filed five times should not read as five incidents.
        await db.rollback()
        raise ConflictError("You have already reported this debate.") from None

    await db.refresh(report)
    # Logged at warning: nothing reads the table in the MVP, so the log is the only place a
    # report is visible to anyone at all. The claim and the detail are deliberately not
    # logged — they may quote exactly the abuse being reported.
    logger.warning(
        "Debate reported",
        extra={
            "room_id": str(room_id),
            "category": category,
            "reported_user_id": str(opponent.id),
        },
    )
    return ReportRead.model_validate(report)


async def has_reported(db: AsyncSession, room_id: uuid.UUID, user: User) -> bool:
    """Whether the caller has already reported this debate, so the UI can say so."""
    return await report_repo.get_report_by_reporter(db, room_id, user.id) is not None
