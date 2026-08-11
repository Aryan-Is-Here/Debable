"""Matchmaking rules, against a real database."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Topic, User
from app.models.topic import TopicStatus
from app.repositories import match as match_repo
from app.schemas.match import MatchStatus
from app.services import match as match_service
from app.services import topic as topic_service
from tests.conftest import make_topic


@pytest.fixture
async def topic(db_session: AsyncSession, user: User) -> Topic:
    record = make_topic(user)
    db_session.add(record)
    await db_session.flush()
    return record


async def test_a_lone_user_waits(db_session: AsyncSession, user: User, topic: Topic) -> None:
    state = await match_service.join(db_session, user, topic.id)

    assert state.status is MatchStatus.QUEUED
    assert state.topic is not None and state.topic.id == topic.id
    assert state.queued_at is not None
    assert state.waiting_count == 1
    assert state.room is None


async def test_second_user_on_the_same_topic_is_paired(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)

    state = await match_service.join(db_session, other_user, topic.id)

    assert state.status is MatchStatus.MATCHED
    assert state.room is not None
    assert state.room.you.id == other_user.id
    assert state.room.opponent.id == user.id
    assert state.room.topic.id == topic.id


async def test_the_waiting_user_discovers_the_match_on_their_next_poll(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    """The first user never called join again — the room has to surface via polling."""
    await match_service.join(db_session, user, topic.id)
    await match_service.join(db_session, other_user, topic.id)

    state = await match_service.get_state(db_session, user)

    assert state.status is MatchStatus.MATCHED
    assert state.room is not None
    # Each side sees itself as "you".
    assert state.room.you.id == user.id
    assert state.room.opponent.id == other_user.id


async def test_pairing_empties_the_queue(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    await match_service.join(db_session, other_user, topic.id)

    assert await match_repo.get_queue_entry(db_session, user.id) is None
    assert await match_repo.get_queue_entry(db_session, other_user.id) is None


async def test_users_waiting_on_different_topics_are_not_paired(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    another = make_topic(user, title="A completely different debate topic")
    db_session.add(another)
    await db_session.flush()

    await match_service.join(db_session, user, topic.id)
    state = await match_service.join(db_session, other_user, another.id)

    assert state.status is MatchStatus.QUEUED


async def test_a_user_cannot_be_matched_with_themselves(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)

    state = await match_service.join(db_session, user, topic.id)

    assert state.status is MatchStatus.QUEUED
    assert state.room is None


async def test_switching_topics_replaces_the_queue_entry(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    another = make_topic(user, title="A second topic worth arguing about")
    db_session.add(another)
    await db_session.flush()

    await match_service.join(db_session, user, topic.id)
    await match_service.join(db_session, user, another.id)

    entry = await match_repo.get_queue_entry(db_session, user.id)
    assert entry is not None
    assert entry.topic_id == another.id


async def test_joining_while_already_in_a_room_returns_that_room(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    matched = await match_service.join(db_session, other_user, topic.id)

    again = await match_service.join(db_session, other_user, topic.id)

    assert again.status is MatchStatus.MATCHED
    assert again.room is not None
    assert matched.room is not None
    assert again.room.id == matched.room.id


async def test_leaving_the_queue_returns_the_user_to_idle(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)

    await match_service.leave(db_session, user)

    assert (await match_service.get_state(db_session, user)).status is MatchStatus.IDLE


async def test_a_cancelled_user_is_no_longer_matchable(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    await match_service.leave(db_session, user)

    state = await match_service.join(db_session, other_user, topic.id)

    assert state.status is MatchStatus.QUEUED


async def test_leaving_when_not_queued_is_harmless(db_session: AsyncSession, user: User) -> None:
    state = await match_service.leave(db_session, user)

    assert state.status is MatchStatus.IDLE


async def test_queueing_for_an_unknown_topic_raises(db_session: AsyncSession, user: User) -> None:
    with pytest.raises(NotFoundError):
        await match_service.join(db_session, user, uuid.uuid4())


async def test_archived_topics_reject_new_debates(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    topic.status = TopicStatus.ARCHIVED
    await db_session.flush()

    with pytest.raises(ConflictError):
        await match_service.join(db_session, user, topic.id)


async def test_a_non_participant_cannot_read_the_room(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    state = await match_service.join(db_session, other_user, topic.id)
    assert state.room is not None

    intruder = User(
        clerk_user_id="user_test_intruder",
        username="intruder",
        email="intruder@example.com",
    )
    db_session.add(intruder)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await match_service.get_room(db_session, state.room.id, intruder)


async def test_ending_a_debate_frees_both_users(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    state = await match_service.join(db_session, other_user, topic.id)
    assert state.room is not None

    ended = await match_service.end_room(db_session, state.room.id, user)

    assert ended.ended_at is not None
    assert (await match_service.get_state(db_session, user)).status is MatchStatus.IDLE
    assert (await match_service.get_state(db_session, other_user)).status is MatchStatus.IDLE


async def test_ending_a_debate_twice_keeps_the_original_end_time(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    state = await match_service.join(db_session, other_user, topic.id)
    assert state.room is not None

    first = await match_service.end_room(db_session, state.room.id, user)
    second = await match_service.end_room(db_session, state.room.id, other_user)

    assert first.ended_at == second.ended_at


async def test_waiting_count_feeds_the_topic_list(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    """activeDebaters was hardcoded to 0 until this phase — it is now the queue size."""
    before = await topic_service.list_topics(db_session)
    assert before.items[0].active_debaters == 0

    await match_service.join(db_session, user, topic.id)

    after = await topic_service.list_topics(db_session)
    assert after.items[0].active_debaters == 1
