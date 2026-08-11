"""Topic repository and service rules, against a real database."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError
from app.models import User
from app.models.topic import TopicStatus
from app.schemas.topic import TopicCreate
from app.services import topic as topic_service
from tests.conftest import make_topic


async def test_created_topic_is_persisted_and_owned_by_the_creator(
    db_session: AsyncSession, user: User
) -> None:
    payload = TopicCreate(
        title="Should social media be age restricted",
        description="Debating whether under-16s should be barred from social platforms.",
        category="Society",
    )

    created = await topic_service.create_topic(db_session, payload, creator_id=user.id)

    assert created.creator.id == user.id
    assert created.status is TopicStatus.OPEN
    assert created.category == "Society"

    # Read it back through a separate query to prove it actually hit the database.
    fetched = await topic_service.get_topic(db_session, created.id)
    assert fetched.title == payload.title


async def test_duplicate_titles_are_rejected_regardless_of_case(
    db_session: AsyncSession, user: User
) -> None:
    payload = TopicCreate(
        title="Should nuclear power expand",
        description="Debating whether nuclear energy deserves a larger share of the grid.",
        category="Environment",
    )
    await topic_service.create_topic(db_session, payload, creator_id=user.id)

    duplicate = payload.model_copy(update={"title": "should NUCLEAR power expand"})
    with pytest.raises(ConflictError):
        await topic_service.create_topic(db_session, duplicate, creator_id=user.id)


async def test_getting_an_unknown_topic_raises_not_found(db_session: AsyncSession) -> None:
    with pytest.raises(NotFoundError):
        await topic_service.get_topic(db_session, uuid.uuid4())


async def test_search_matches_title_and_description_case_insensitively(
    db_session: AsyncSession, user: User
) -> None:
    db_session.add_all(
        [
            make_topic(user, title="Remote work is here to stay", category="Economics"),
            make_topic(
                user,
                title="Cities should be car free",
                description="A debate about banning private CARS from city centres.",
                category="Environment",
            ),
        ]
    )
    await db_session.flush()

    by_title = await topic_service.list_topics(db_session, search="REMOTE")
    by_description = await topic_service.list_topics(db_session, search="cars")

    assert [t.title for t in by_title.items] == ["Remote work is here to stay"]
    assert [t.title for t in by_description.items] == ["Cities should be car free"]


async def test_category_filter_is_exact(db_session: AsyncSession, user: User) -> None:
    db_session.add_all(
        [
            make_topic(user, title="Topic about technology today", category="Technology"),
            make_topic(user, title="Topic about health systems", category="Health"),
        ]
    )
    await db_session.flush()

    page = await topic_service.list_topics(db_session, category="Health")

    assert [t.category for t in page.items] == ["Health"]
    assert page.total == 1


async def test_newest_topics_come_first(db_session: AsyncSession, user: User) -> None:
    # Timestamps are set explicitly rather than left to the column default: Postgres' now()
    # is the *transaction* clock, so rows inserted in one transaction would all tie.
    base = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    for index in range(3):
        db_session.add(
            make_topic(
                user,
                title=f"Debate number {index} about policy",
                created_at=base + timedelta(minutes=index),
            )
        )
    await db_session.flush()

    page = await topic_service.list_topics(db_session)

    assert [t.title for t in page.items] == [
        "Debate number 2 about policy",
        "Debate number 1 about policy",
        "Debate number 0 about policy",
    ]


async def test_paging_reports_the_unpaged_total(db_session: AsyncSession, user: User) -> None:
    for index in range(5):
        db_session.add(make_topic(user, title=f"Paging debate number {index} here"))
    await db_session.flush()

    page = await topic_service.list_topics(db_session, limit=2, offset=2)

    assert len(page.items) == 2
    assert page.total == 5
    assert page.offset == 2


async def test_page_size_is_capped(db_session: AsyncSession, user: User) -> None:
    page = await topic_service.list_topics(db_session, limit=10_000)

    assert page.limit == topic_service.MAX_PAGE_SIZE


async def test_filters_combine(db_session: AsyncSession, user: User) -> None:
    db_session.add_all(
        [
            make_topic(user, title="Climate policy needs teeth", category="Environment"),
            make_topic(user, title="Climate science communication", category="Science"),
        ]
    )
    await db_session.flush()

    page = await topic_service.list_topics(db_session, search="climate", category="Science")

    assert [t.title for t in page.items] == ["Climate science communication"]
