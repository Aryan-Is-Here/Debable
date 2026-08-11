"""Concurrent matchmaking.

These tests use real, separately-committed connections rather than the shared
transactional ``db_session`` — row locking is invisible inside a single transaction, and
row locking is the entire point of the design. Rows are cleaned up explicitly at the end.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine

from app.models import DebateRoom, MatchQueueEntry, Topic, User
from app.schemas.match import MatchStatus
from app.services import match as match_service


@pytest_asyncio.fixture
async def engine(database_url: str) -> AsyncIterator[AsyncEngine]:
    created = create_async_engine(database_url)
    yield created
    await created.dispose()


@pytest_asyncio.fixture
async def committed_world(engine: AsyncEngine) -> AsyncIterator[tuple[Topic, list[User]]]:
    """Three users and a topic, committed so separate connections can see them."""
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    marker = uuid.uuid4().hex[:8]

    async with factory() as session:
        users = [
            User(
                clerk_user_id=f"user_conc_{marker}_{index}",
                username=f"racer_{marker}_{index}",
                email=f"racer_{marker}_{index}@example.com",
            )
            for index in range(3)
        ]
        session.add_all(users)
        await session.flush()
        topic = Topic(
            title=f"Concurrency debate {marker} about locking",
            description="Whether two requests can claim the same opponent at the same time.",
            category="Technology",
            creator_id=users[0].id,
        )
        session.add(topic)
        await session.commit()
        user_ids = [user.id for user in users]
        topic_id = topic.id

    try:
        yield topic, users
    finally:
        async with factory() as session:
            await session.execute(delete(DebateRoom).where(DebateRoom.topic_id == topic_id))
            await session.execute(
                delete(MatchQueueEntry).where(MatchQueueEntry.user_id.in_(user_ids))
            )
            await session.execute(delete(Topic).where(Topic.id == topic_id))
            await session.execute(delete(User).where(User.id.in_(user_ids)))
            await session.commit()


async def _join(engine: AsyncEngine, user: User, topic_id: uuid.UUID):
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        return await match_service.join(session, user, topic_id)


async def test_two_simultaneous_joins_cannot_claim_the_same_opponent(
    engine: AsyncEngine, committed_world: tuple[Topic, list[User]]
) -> None:
    """The invariant: a waiting user ends up in exactly one room, never two."""
    topic, users = committed_world
    waiting, first_challenger, second_challenger = users

    await _join(engine, waiting, topic.id)

    # Both challengers race for the single waiting opponent.
    results = await asyncio.gather(
        _join(engine, first_challenger, topic.id),
        _join(engine, second_challenger, topic.id),
        return_exceptions=True,
    )
    for result in results:
        assert not isinstance(result, BaseException), result

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        rooms = (
            await session.scalars(select(DebateRoom).where(DebateRoom.topic_id == topic.id))
        ).all()

    rooms_with_waiting = [room for room in rooms if waiting.id in (room.user1_id, room.user2_id)]
    assert len(rooms_with_waiting) == 1, "the waiting user was matched more than once"

    # And nobody is double-booked.
    seen: set[uuid.UUID] = set()
    for room in rooms:
        for participant in (room.user1_id, room.user2_id):
            assert participant not in seen, "a user was placed in two rooms at once"
            seen.add(participant)

    statuses = [result.status for result in results]  # type: ignore[union-attr]
    assert MatchStatus.MATCHED in statuses


async def test_a_user_can_hold_only_one_place_in_the_queue(
    engine: AsyncEngine, committed_world: tuple[Topic, list[User]]
) -> None:
    """The unique constraint holds even when two joins arrive together."""
    topic, users = committed_world
    solo = users[0]

    results = await asyncio.gather(
        _join(engine, solo, topic.id),
        _join(engine, solo, topic.id),
        return_exceptions=True,
    )

    # One may lose the race with a conflict; neither may corrupt the queue.
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as session:
        entries = (
            await session.scalars(select(MatchQueueEntry).where(MatchQueueEntry.user_id == solo.id))
        ).all()

    assert len(entries) <= 1
    assert any(not isinstance(result, BaseException) for result in results)
