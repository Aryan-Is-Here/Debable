"""Topic endpoints.

``GET`` is public — Browse must work for a signed-out visitor, since seeing what people are
debating is how the product sells itself. ``POST`` requires a verified Clerk session.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, OptionalUser
from app.core.categories import TOPIC_CATEGORIES
from app.db.session import get_db
from app.models.topic import TopicStatus
from app.schemas.common import Page
from app.schemas.topic import TopicCreate, TopicRead
from app.services import topic as topic_service

router = APIRouter(prefix="/topics", tags=["topics"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get(
    "/categories",
    response_model=list[str],
    summary="Allowed topic categories",
)
async def list_categories() -> list[str]:
    """The category allowlist.

    Declared before ``/{topic_id}`` so the literal path wins over the UUID route.
    """
    return list(TOPIC_CATEGORIES)


@router.get(
    "",
    response_model=Page[TopicRead],
    summary="List topics",
)
async def list_topics(
    db: DbSession,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Case-insensitive match on title or description."),
    ] = None,
    category: Annotated[str | None, Query(description="Exact category name.")] = None,
    status_filter: Annotated[
        TopicStatus | None, Query(alias="status", description="Lifecycle filter.")
    ] = None,
    mine: Annotated[
        bool,
        Query(description="Only topics you created. Requires a signed-in caller."),
    ] = False,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    current_user: OptionalUser = None,
) -> Page[TopicRead]:
    """Browse topics. Anonymous callers see everything except the `mine` filter.

    `mine` exists so the profile screen can list what you created without a second endpoint
    that would duplicate this one's paging and filtering. A `mine=true` from an anonymous
    caller returns nothing rather than everything — silently ignoring the filter would show a
    stranger's topics under "Topics created".
    """
    creator_id = None
    if mine:
        if current_user is None:
            return Page[TopicRead](items=[], total=0, limit=limit, offset=offset)
        creator_id = current_user.id

    return await topic_service.list_topics(
        db,
        search=search,
        category=category,
        status=status_filter,
        creator_id=creator_id,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{topic_id}",
    response_model=TopicRead,
    summary="Get one topic",
    responses={404: {"description": "No topic with that id."}},
)
async def get_topic(topic_id: uuid.UUID, db: DbSession) -> TopicRead:
    return await topic_service.get_topic(db, topic_id)


@router.post(
    "",
    response_model=TopicRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a topic",
    responses={
        401: {"description": "Missing or invalid Clerk session token."},
        409: {"description": "A topic with this title already exists."},
    },
)
async def create_topic(payload: TopicCreate, current_user: CurrentUser, db: DbSession) -> TopicRead:
    return await topic_service.create_topic(db, payload, creator_id=current_user.id)
