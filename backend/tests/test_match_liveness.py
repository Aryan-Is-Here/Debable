"""Queue liveness.

Regression cover for the ghost-opponent bug: a closed browser tab left its queue row
behind, and the next person to pick that topic was matched against someone who was not
there. Presence is now proven by continuing to poll.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MatchQueueEntry, Topic, User
from app.repositories import match as match_repo
from app.repositories.match import QUEUE_STALE_AFTER
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


async def _age_entry(db_session: AsyncSession, user_id, age: timedelta) -> None:
    """Backdate a user's heartbeat, simulating a tab that stopped polling."""
    entry = await db_session.scalar(
        MatchQueueEntry.__table__.select().where(MatchQueueEntry.user_id == user_id)
    )
    assert entry is not None, "expected the user to be queued"
    await db_session.execute(
        MatchQueueEntry.__table__.update()
        .where(MatchQueueEntry.user_id == user_id)
        .values(last_seen_at=datetime.now(UTC) - age)
    )


async def test_a_stale_entry_is_not_offered_as_an_opponent(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    """The bug: someone who closed their tab was still matchable."""
    await match_service.join(db_session, user, topic.id)
    await _age_entry(db_session, user.id, QUEUE_STALE_AFTER + timedelta(seconds=5))

    state = await match_service.join(db_session, other_user, topic.id)

    assert state.status is MatchStatus.QUEUED, "matched against an abandoned queue entry"


async def test_a_fresh_entry_is_still_matchable(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    """The guard must not be so eager that it breaks normal matching."""
    await match_service.join(db_session, user, topic.id)
    await _age_entry(db_session, user.id, QUEUE_STALE_AFTER - timedelta(seconds=10))

    state = await match_service.join(db_session, other_user, topic.id)

    assert state.status is MatchStatus.MATCHED


async def test_stale_entries_do_not_inflate_the_waiting_count(
    db_session: AsyncSession, user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    await _age_entry(db_session, user.id, QUEUE_STALE_AFTER + timedelta(seconds=5))

    listing = await topic_service.list_topics(db_session)

    assert listing.items[0].active_debaters == 0


async def test_stale_entries_are_swept_away(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, user, topic.id)
    await _age_entry(db_session, user.id, QUEUE_STALE_AFTER + timedelta(seconds=5))

    removed = await match_repo.sweep_stale(db_session)

    assert removed == 1
    assert await match_repo.get_queue_entry(db_session, user.id) is None


async def test_polling_keeps_the_caller_in_the_queue(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    """A waiting user who keeps polling must never be swept, however long they wait."""
    await match_service.join(db_session, user, topic.id)
    await _age_entry(db_session, user.id, QUEUE_STALE_AFTER + timedelta(seconds=5))

    # The heartbeat happens before the sweep, so the caller survives their own cleanup.
    state = await match_service.get_state(db_session, user)

    assert state.status is MatchStatus.QUEUED
    assert (await match_service.join(db_session, other_user, topic.id)).status is (
        MatchStatus.MATCHED
    )


async def test_a_polling_user_sweeps_away_someone_elses_dead_entry(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    await match_service.join(db_session, other_user, topic.id)
    await _age_entry(db_session, other_user.id, QUEUE_STALE_AFTER + timedelta(seconds=5))
    await match_service.join(db_session, user, topic.id)

    await match_service.get_state(db_session, user)

    assert await match_repo.get_queue_entry(db_session, other_user.id) is None
