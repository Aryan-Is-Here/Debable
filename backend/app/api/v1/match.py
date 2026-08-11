"""Matchmaking and debate room endpoints.

Everything here requires a signed-in user: you cannot queue anonymously, and rooms are
visible only to their two participants.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.db.session import get_db
from app.schemas.match import DebateRoomRead, MatchRequest, MatchState
from app.services import match as match_service

router = APIRouter(tags=["matchmaking"])

DbSession = Annotated[AsyncSession, Depends(get_db)]

_AUTH_RESPONSES = {401: {"description": "Missing or invalid Clerk session token."}}


@router.post(
    "/match",
    response_model=MatchState,
    summary="Join the matchmaking queue",
    responses={
        **_AUTH_RESPONSES,
        404: {"description": "No such topic."},
        409: {"description": "The topic is archived."},
    },
)
async def join_queue(payload: MatchRequest, current_user: CurrentUser, db: DbSession) -> MatchState:
    """Queue for a topic.

    Returns `matched` immediately when someone was already waiting, otherwise `queued` —
    poll `GET /match` until it flips.
    """
    return await match_service.join(db, current_user, payload.topic_id)


@router.get(
    "/match",
    response_model=MatchState,
    summary="Poll matchmaking status",
    responses=_AUTH_RESPONSES,
)
async def get_status(current_user: CurrentUser, db: DbSession) -> MatchState:
    return await match_service.get_state(db, current_user)


@router.delete(
    "/match",
    response_model=MatchState,
    summary="Leave the matchmaking queue",
    responses=_AUTH_RESPONSES,
)
async def leave_queue(current_user: CurrentUser, db: DbSession) -> MatchState:
    return await match_service.leave(db, current_user)


@router.get(
    "/rooms/{room_id}",
    response_model=DebateRoomRead,
    summary="Get a debate room",
    responses={
        **_AUTH_RESPONSES,
        403: {"description": "You are not a participant in this debate."},
        404: {"description": "No such room."},
    },
)
async def get_room(room_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> DebateRoomRead:
    return await match_service.get_room(db, room_id, current_user)


@router.post(
    "/rooms/{room_id}/end",
    response_model=DebateRoomRead,
    status_code=status.HTTP_200_OK,
    summary="End a debate",
    responses={
        **_AUTH_RESPONSES,
        403: {"description": "You are not a participant in this debate."},
        404: {"description": "No such room."},
    },
)
async def end_room(room_id: uuid.UUID, current_user: CurrentUser, db: DbSession) -> DebateRoomRead:
    """Either participant may end the debate; calling it twice is harmless."""
    return await match_service.end_room(db, room_id, current_user)
