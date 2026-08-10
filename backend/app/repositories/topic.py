"""Topic queries and persistence."""

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.topic import Topic, TopicStatus


def _base_query(
    *,
    search: str | None,
    category: str | None,
    status: TopicStatus | None,
    creator_id: uuid.UUID | None,
) -> Select[tuple[Topic]]:
    """Build the filter clause shared by the list query and its count."""
    query = select(Topic)

    if search:
        # ILIKE rather than full-text search: the corpus is small and a trigram/tsvector
        # index is not worth its complexity until the topic list is large enough to feel slow.
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Topic.title.ilike(pattern), Topic.description.ilike(pattern)))
    if category:
        query = query.where(Topic.category == category)
    if status is not None:
        query = query.where(Topic.status == status)
    if creator_id is not None:
        query = query.where(Topic.creator_id == creator_id)

    return query


async def list_topics(
    db: AsyncSession,
    *,
    search: str | None = None,
    category: str | None = None,
    status: TopicStatus | None = None,
    creator_id: uuid.UUID | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[Topic], int]:
    """Return a page of topics newest-first, plus the total number of matches."""
    query = _base_query(search=search, category=category, status=status, creator_id=creator_id)

    total = await db.scalar(select(func.count()).select_from(query.order_by(None).subquery()))

    result = await db.scalars(
        query.options(selectinload(Topic.creator))
        .order_by(Topic.created_at.desc(), Topic.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.all(), total or 0


async def get_topic(db: AsyncSession, topic_id: uuid.UUID) -> Topic | None:
    """Return one topic with its creator loaded, or ``None``."""
    return await db.scalar(
        select(Topic).options(selectinload(Topic.creator)).where(Topic.id == topic_id)
    )


async def create_topic(
    db: AsyncSession,
    *,
    title: str,
    description: str,
    category: str,
    creator_id: uuid.UUID,
) -> Topic:
    """Insert a topic and return it with its creator loaded.

    Flushes rather than commits — the caller owns the transaction boundary.
    """
    topic = Topic(
        title=title,
        description=description,
        category=category,
        creator_id=creator_id,
        status=TopicStatus.OPEN,
    )
    db.add(topic)
    await db.flush()
    await db.refresh(topic, attribute_names=["creator", "created_at", "updated_at", "status"])
    return topic


async def title_exists(db: AsyncSession, title: str) -> bool:
    """Whether an identically-titled topic already exists, ignoring case and padding."""
    normalised = title.strip()
    return bool(
        await db.scalar(
            select(func.count()).select_from(Topic).where(Topic.title.ilike(normalised))
        )
    )
