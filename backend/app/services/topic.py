"""Topic business rules."""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models.topic import Topic, TopicStatus
from app.repositories import topic as topic_repo
from app.schemas.common import Page
from app.schemas.topic import TopicCreate, TopicRead

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 50


async def list_topics(
    db: AsyncSession,
    *,
    search: str | None = None,
    category: str | None = None,
    status: TopicStatus | None = None,
    creator_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> Page[TopicRead]:
    """Return a page of topics matching the given filters."""
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = max(0, offset)

    topics, total = await topic_repo.list_topics(
        db,
        search=search,
        category=category,
        status=status,
        creator_id=creator_id,
        limit=limit,
        offset=offset,
    )
    return Page[TopicRead](
        items=[TopicRead.model_validate(topic) for topic in topics],
        total=total,
        limit=limit,
        offset=offset,
    )


async def get_topic(db: AsyncSession, topic_id: uuid.UUID) -> TopicRead:
    """Return one topic, or raise ``NotFoundError``."""
    topic = await topic_repo.get_topic(db, topic_id)
    if topic is None:
        raise NotFoundError("Topic not found.")
    return TopicRead.model_validate(topic)


async def create_topic(db: AsyncSession, payload: TopicCreate, creator_id: uuid.UUID) -> TopicRead:
    """Create a topic owned by ``creator_id``.

    Duplicate titles are rejected: two identically-named topics would split debaters across
    two matchmaking pools, which is the opposite of what the topic is for.
    """
    if await topic_repo.title_exists(db, payload.title):
        raise ConflictError("A topic with this title already exists.")

    topic: Topic = await topic_repo.create_topic(
        db,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        creator_id=creator_id,
    )
    await db.commit()

    logger.info(
        "Topic created",
        extra={"topic_id": str(topic.id), "creator_id": str(creator_id)},
    )
    return TopicRead.model_validate(topic)
