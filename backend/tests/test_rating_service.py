"""Rating rules and the profile aggregates built from them."""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import DebateRoom, User
from app.services import rating as rating_service
from tests.conftest import make_topic


async def _end(db: AsyncSession, room: DebateRoom) -> DebateRoom:
    room.ended_at = datetime.now(UTC)
    await db.flush()
    return room


async def _make_room(
    db: AsyncSession, first: User, second: User, *, title: str = "Another debate topic here"
) -> DebateRoom:
    topic = make_topic(first, title=title)
    db.add(topic)
    await db.flush()
    room = DebateRoom(topic_id=topic.id, user1_id=first.id, user2_id=second.id)
    db.add(room)
    await db.flush()
    return room


# --- Submitting ------------------------------------------------------------------------


async def test_a_participant_rates_their_opponent(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await _end(db_session, debate_room)

    rating = await rating_service.submit(
        db_session, debate_room.id, user, score=4, comment="Well argued."
    )

    assert rating.score == 4
    assert rating.reviewer_id == user.id
    # The rating attaches to the opponent, never the reviewer — there is a CHECK constraint
    # forbidding self-review, but the service must not rely on hitting it.
    assert rating.reviewed_user_id == other_user.id


async def test_rating_twice_is_refused_rather_than_overwriting(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """An overwrite would let someone revise a score after seeing the reply."""
    await _end(db_session, debate_room)
    # Captured before the duplicate attempt: the service's `db.rollback()` expires every ORM
    # object in the session, and these tests share one session where the application uses one
    # per request. Reading `debate_room.id` afterwards would lazily reload it, synchronously,
    # outside the async greenlet — a test artifact rather than a production path, since the
    # service raises immediately after rolling back and touches no ORM object again.
    room_id = debate_room.id
    first = await rating_service.submit(db_session, room_id, user, score=5, comment=None)

    with pytest.raises(ConflictError, match="already rated"):
        await rating_service.submit(db_session, room_id, user, score=1, comment=None)

    state = await rating_service.get_state(db_session, room_id, user)
    assert state.submitted is True
    assert state.rating is not None
    # The original survived intact.
    assert state.rating.id == first.id
    assert state.rating.score == 5


async def test_both_debaters_may_rate_the_same_debate(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    """The constraint is per reviewer, not per room."""
    await _end(db_session, debate_room)

    await rating_service.submit(db_session, debate_room.id, user, score=4, comment=None)
    await rating_service.submit(db_session, debate_room.id, other_user, score=2, comment=None)

    mine = await rating_service.get_state(db_session, debate_room.id, user)
    theirs = await rating_service.get_state(db_session, debate_room.id, other_user)
    assert mine.rating is not None and theirs.rating is not None
    assert mine.rating.id != theirs.rating.id


async def test_an_unfinished_debate_cannot_be_rated(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """Rating mid-argument would measure its temperature, not the debate."""
    with pytest.raises(ConflictError, match="not finished"):
        await rating_service.submit(db_session, debate_room.id, user, score=5, comment=None)


async def test_a_non_participant_cannot_rate(
    db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    await _end(db_session, debate_room)
    outsider = User(
        clerk_user_id="user_test_outsider",
        username="outsider",
        email="outsider@example.com",
        avatar_url=None,
    )
    db_session.add(outsider)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await rating_service.submit(db_session, debate_room.id, outsider, score=1, comment=None)


async def test_an_unknown_room_is_not_found(db_session: AsyncSession, user: User) -> None:
    with pytest.raises(NotFoundError):
        await rating_service.submit(db_session, uuid.uuid4(), user, score=3, comment=None)


async def test_state_is_unsubmitted_before_rating(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    state = await rating_service.get_state(db_session, debate_room.id, user)

    assert state.submitted is False
    assert state.rating is None


# --- Profile ---------------------------------------------------------------------------


async def test_a_new_profile_has_no_average_rather_than_a_zero(
    db_session: AsyncSession, user: User
) -> None:
    """There is no honest number for "not yet rated" — a 0 reads as terrible, a 5 is a lie."""
    profile = await rating_service.get_profile(db_session, user)

    assert profile.average_rating is None
    assert profile.debates_count == 0
    assert profile.history == []


async def test_the_profile_counts_only_finished_debates(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    """A debate in progress is not history."""
    await _end(db_session, debate_room)
    await _make_room(db_session, user, other_user, title="A debate still going on now")

    profile = await rating_service.get_profile(db_session, user)

    assert profile.debates_count == 1


async def test_the_profile_reports_ratings_received_not_given(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await _end(db_session, debate_room)
    # `user` rates `other_user` a 2. That must not appear on `user`'s own average.
    await rating_service.submit(db_session, debate_room.id, user, score=2, comment=None)
    await rating_service.submit(db_session, debate_room.id, other_user, score=5, comment=None)

    mine = await rating_service.get_profile(db_session, user)
    theirs = await rating_service.get_profile(db_session, other_user)

    assert mine.average_rating == 5.0
    assert theirs.average_rating == 2.0


async def test_history_names_the_opponent_and_the_score_received(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await _end(db_session, debate_room)
    await rating_service.submit(db_session, debate_room.id, other_user, score=4, comment=None)

    profile = await rating_service.get_profile(db_session, user)

    assert len(profile.history) == 1
    entry = profile.history[0]
    assert entry.opponent.id == other_user.id
    assert entry.rating_received == 4
    assert entry.topic_title == debate_room.topic.title


async def test_history_shows_none_for_an_unrated_debate(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """Not every debate gets rated — the results screen has a Skip button."""
    await _end(db_session, debate_room)

    profile = await rating_service.get_profile(db_session, user)

    assert profile.history[0].rating_received is None


async def test_history_is_newest_first(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await _end(db_session, debate_room)
    second = await _make_room(db_session, user, other_user, title="A more recent debate topic")
    await _end(db_session, second)

    profile = await rating_service.get_profile(db_session, user)

    assert [entry.id for entry in profile.history][0] == second.id
