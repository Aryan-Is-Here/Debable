"""Chat rules, without a socket.

Delivery is the WebSocket layer's problem; what is allowed and what is stored is decided
here, and that is worth testing on its own.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import DebateRoom, User
from app.services import chat as chat_service


async def test_a_message_survives_and_comes_back_in_history(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    stored = await chat_service.post_message(db_session, debate_room.id, user, "Opening claim.")

    history = await chat_service.list_history(db_session, debate_room.id, user)

    assert [message.id for message in history] == [stored.id]
    assert history[0].content == "Opening claim."
    assert history[0].sender_id == user.id


async def test_history_is_oldest_first(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    for content in ("first", "second", "third"):
        sender = user if content != "second" else other_user
        await chat_service.post_message(db_session, debate_room.id, sender, content)

    history = await chat_service.list_history(db_session, debate_room.id, user)

    assert [message.content for message in history] == ["first", "second", "third"]


async def test_both_participants_read_the_same_history(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await chat_service.post_message(db_session, debate_room.id, user, "Mine.")
    await chat_service.post_message(db_session, debate_room.id, other_user, "Theirs.")

    mine = await chat_service.list_history(db_session, debate_room.id, user)
    theirs = await chat_service.list_history(db_session, debate_room.id, other_user)

    # Identical because the wire carries sender ids, not a viewer-relative "you"/"opponent".
    assert [m.id for m in mine] == [m.id for m in theirs]


async def test_a_non_participant_cannot_read_history(
    db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    outsider = User(
        clerk_user_id="user_test_outsider",
        username="outsider",
        email="outsider@example.com",
        avatar_url=None,
    )
    db_session.add(outsider)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await chat_service.list_history(db_session, debate_room.id, outsider)


async def test_a_non_participant_cannot_post(
    db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    outsider = User(
        clerk_user_id="user_test_outsider",
        username="outsider",
        email="outsider@example.com",
        avatar_url=None,
    )
    db_session.add(outsider)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await chat_service.post_message(db_session, debate_room.id, outsider, "Let me in.")


async def test_an_unknown_room_is_not_found(db_session: AsyncSession, user: User) -> None:
    with pytest.raises(NotFoundError):
        await chat_service.post_message(db_session, uuid.uuid4(), user, "Anyone there?")


async def test_an_ended_debate_refuses_new_messages(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    debate_room.ended_at = datetime.now(UTC)
    await db_session.flush()

    with pytest.raises(ConflictError):
        await chat_service.post_message(db_session, debate_room.id, user, "One more thing.")


async def test_an_ended_debate_is_still_readable(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """The results screen and a reconnecting client both need a closed room's transcript."""
    await chat_service.post_message(db_session, debate_room.id, user, "Said while live.")
    debate_room.ended_at = datetime.now(UTC)
    await db_session.flush()

    history = await chat_service.list_history(db_session, debate_room.id, user)

    assert [message.content for message in history] == ["Said while live."]
