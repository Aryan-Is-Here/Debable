"""Rating and profile endpoints.

Ratings hang off a room because that is what is being rated — a debate, not a person in the
abstract. The profile endpoint is here rather than in its own module because everything it
reports is derived from ratings and finished rooms.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.rating import RatingCreate, RatingRead, RatingState, UserProfileRead
from app.services import rating as rating_service

router = APIRouter(tags=["ratings"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

_AUTH_RESPONSES = {401: {"description": "Missing or invalid Clerk session token."}}


@router.post(
    "/rooms/{room_id}/rating",
    response_model=RatingRead,
    summary="Rate your opponent after a debate",
    responses={
        **_AUTH_RESPONSES,
        403: {"description": "You were not a participant in this debate."},
        404: {"description": "No such room."},
        409: {"description": "The debate has not ended, or you have already rated it."},
        422: {"description": "Score outside 1–5, or a comment over 300 characters."},
    },
)
async def submit_rating(
    room_id: uuid.UUID,
    payload: RatingCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> RatingRead:
    """Rate the other debater, once, after the debate has ended.

    A second attempt is a 409 rather than an update: allowing an overwrite would let someone
    revise a score after seeing the reply, and would destroy the original silently.
    """
    return await rating_service.submit(
        db, room_id, current_user, score=payload.score, comment=payload.comment
    )


@router.get(
    "/rooms/{room_id}/rating",
    response_model=RatingState,
    summary="Whether you have already rated this debate",
    responses={
        **_AUTH_RESPONSES,
        403: {"description": "You were not a participant in this debate."},
        404: {"description": "No such room."},
    },
)
async def get_rating_state(
    room_id: uuid.UUID, current_user: CurrentUser, db: DbSession
) -> RatingState:
    """Asked before the results screen renders its form, so a revisit shows what was sent."""
    return await rating_service.get_state(db, room_id, current_user)


@router.get(
    "/profile",
    response_model=UserProfileRead,
    summary="Your profile: debates and ratings received",
    responses=_AUTH_RESPONSES,
)
async def get_profile(current_user: CurrentUser, db: DbSession) -> UserProfileRead:
    """The caller's own profile.

    No `/profile/{user_id}`: a public profile would expose who debated whom, and the MVP has
    no privacy controls to make that a considered choice rather than an accident.
    """
    return await rating_service.get_profile(db, current_user)
