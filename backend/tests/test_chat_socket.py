"""The chat WebSocket end to end.

The claim this phase has to make good on is that a message sent by one debater reaches the
other without a refresh, and is still there after one. ``test_a_message_reaches_the_other_
debater`` and ``test_a_broadcast_message_is_in_the_rest_history`` are the two halves of it;
fixtures would pass the first and fail the second.
"""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx_ws import AsyncWebSocketSession, WebSocketDisconnect, aconnect_ws
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DebateRoom, User
from app.services import chat as chat_service
from app.websocket.protocol import (
    CLOSE_FORBIDDEN,
    CLOSE_NOT_FOUND,
    CLOSE_UNAUTHENTICATED,
)
from app.websocket.registry import chat_registry
from tests.conftest import make_topic, open_ws_client


def chat_url(room_id: uuid.UUID) -> str:
    return f"http://test/api/v1/rooms/{room_id}/chat"


@asynccontextmanager
async def open_socket(app: FastAPI, room_id: uuid.UUID) -> AsyncIterator[AsyncWebSocketSession]:
    """An unauthenticated socket on a room, with its client scoped to the caller's task."""
    async with open_ws_client(app) as client, aconnect_ws(chat_url(room_id), client) as ws:
        yield ws


async def authenticate(ws: AsyncWebSocketSession, token: str) -> dict:
    """Send the auth frame and return the ``ready`` frame."""
    await ws.send_json({"type": "auth", "token": token})
    return await ws.receive_json()


def close_code(error: BaseException) -> int | None:
    """Dig a ``WebSocketDisconnect``'s code out of however deeply it is wrapped.

    The unwrapping is not incidental: httpx-ws runs the ASGI app inside nested anyio task
    groups, so a disconnect raised in the handler reaches the test inside an
    ``ExceptionGroup`` containing another ``ExceptionGroup``. Asserting on the outer
    exception would fail for a thoroughly confusing reason.
    """
    if isinstance(error, WebSocketDisconnect):
        return error.code
    if isinstance(error, BaseExceptionGroup):
        for inner in error.exceptions:
            code = close_code(inner)
            if code is not None:
                return code
    return None


async def refusal_code(app: FastAPI, room_id: uuid.UUID, token: str) -> int:
    """Attempt to connect and return the code the server closed with."""
    try:
        async with open_socket(app, room_id) as ws:
            await authenticate(ws, token)
    except BaseException as error:  # noqa: BLE001 - re-raised below unless it is a disconnect
        code = close_code(error)
        if code is None:
            raise
        return code
    raise AssertionError("The socket was not closed.")


async def test_authenticating_yields_a_ready_frame(
    ws_app: FastAPI, debate_room: DebateRoom, user: User
) -> None:
    async with open_socket(ws_app, debate_room.id) as ws:
        ready = await authenticate(ws, "token-primary")

    assert ready["type"] == "ready"
    assert ready["roomId"] == str(debate_room.id)
    # The client needs its own id to tell "you" from "opponent" when rendering senderId.
    assert ready["userId"] == str(user.id)


async def test_an_invalid_token_closes_the_socket(ws_app: FastAPI, debate_room: DebateRoom) -> None:
    code = await refusal_code(ws_app, debate_room.id, "not-a-real-token")
    assert code == CLOSE_UNAUTHENTICATED


async def test_a_non_auth_first_frame_is_refused(ws_app: FastAPI, debate_room: DebateRoom) -> None:
    """Nothing is accepted before authentication — not even a well-formed message."""
    try:
        async with open_socket(ws_app, debate_room.id) as ws:
            await ws.send_json({"type": "message", "content": "sneaking in"})
            await ws.receive_json()
    except BaseException as error:  # noqa: BLE001 - re-raised below unless it is a disconnect
        code = close_code(error)
        if code is None:
            raise
        assert code == CLOSE_UNAUTHENTICATED
    else:
        raise AssertionError("An unauthenticated message frame was accepted.")


async def test_a_non_participant_is_refused(
    ws_app: FastAPI, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    outsider = User(
        clerk_user_id="user_test_outsider",
        username="outsider",
        email="outsider@example.com",
        avatar_url=None,
    )
    db_session.add(outsider)
    await db_session.flush()

    assert await refusal_code(ws_app, debate_room.id, "token-outsider") == CLOSE_FORBIDDEN


async def test_an_unknown_room_is_refused(ws_app: FastAPI, user: User) -> None:
    assert await refusal_code(ws_app, uuid.uuid4(), "token-primary") == CLOSE_NOT_FOUND


async def test_a_message_reaches_the_other_debater(
    ws_app: FastAPI, debate_room: DebateRoom, user: User
) -> None:
    """The point of the phase: no refresh, no poll — it simply arrives."""
    async with open_socket(ws_app, debate_room.id) as sender:
        await authenticate(sender, "token-primary")
        async with open_socket(ws_app, debate_room.id) as receiver:
            await authenticate(receiver, "token-secondary")

            await sender.send_json({"type": "message", "content": "Automation cuts both ways."})

            received = await receiver.receive_json()
            echoed = await sender.receive_json()

    assert received["type"] == "message"
    assert received["message"]["content"] == "Automation cuts both ways."
    assert received["message"]["senderId"] == str(user.id)
    # Echoed to the sender too, so both windows render the row the server stored rather
    # than one of them rendering optimistic local state.
    assert echoed["message"]["id"] == received["message"]["id"]


async def test_a_broadcast_message_is_in_the_rest_history(
    ws_app: FastAPI, api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    """The half fixtures would fail: it survives the socket and reloads with the page."""
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")
        await ws.send_json({"type": "message", "content": "Persisted, not just delivered."})
        await ws.receive_json()

    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/messages")

    contents = [message["content"] for message in response.json()["messages"]]
    assert contents == ["Persisted, not just delivered."]


async def test_messages_arrive_in_order(ws_app: FastAPI, debate_room: DebateRoom) -> None:
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")
        for content in ("one", "two", "three"):
            await ws.send_json({"type": "message", "content": content})
        received = [(await ws.receive_json())["message"]["content"] for _ in range(3)]

    assert received == ["one", "two", "three"]


async def test_an_empty_message_is_refused_without_dropping_the_socket(
    ws_app: FastAPI, debate_room: DebateRoom
) -> None:
    """A typo should not cost you the connection."""
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")

        await ws.send_json({"type": "message", "content": "   "})
        error = await ws.receive_json()

        # Still usable afterwards.
        await ws.send_json({"type": "message", "content": "A real point."})
        followup = await ws.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "validation_error"
    assert followup["type"] == "message"
    assert followup["message"]["content"] == "A real point."


async def test_an_overlong_message_is_refused(ws_app: FastAPI, debate_room: DebateRoom) -> None:
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")
        await ws.send_json({"type": "message", "content": "x" * 2001})
        error = await ws.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "validation_error"


async def test_an_ended_debate_refuses_messages_but_stays_connected(
    ws_app: FastAPI, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    """Ending mid-conversation must not disconnect anyone — the transcript stays readable."""
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")

        debate_room.ended_at = datetime.now(UTC)
        await db_session.flush()

        await ws.send_json({"type": "message", "content": "One last word."})
        error = await ws.receive_json()

    assert error["type"] == "error"
    assert error["code"] == "conflict"


async def test_a_closed_socket_leaves_the_registry(
    ws_app: FastAPI, debate_room: DebateRoom
) -> None:
    """A leaked entry would make every later broadcast try and fail on a dead peer."""
    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")
        assert await chat_registry.connection_count(debate_room.id) == 1

    assert await chat_registry.connection_count(debate_room.id) == 0


async def test_a_message_is_not_broadcast_to_another_room(
    ws_app: FastAPI,
    db_session: AsyncSession,
    debate_room: DebateRoom,
    user: User,
    other_user: User,
) -> None:
    """Rooms are private; a socket must only ever hear its own debate."""
    topic = make_topic(user, title="A second unrelated debate topic")
    db_session.add(topic)
    await db_session.flush()
    other_room = DebateRoom(topic_id=topic.id, user1_id=user.id, user2_id=other_user.id)
    db_session.add(other_room)
    await db_session.flush()

    async with open_socket(ws_app, debate_room.id) as first:
        await authenticate(first, "token-primary")
        async with open_socket(ws_app, other_room.id) as second:
            await authenticate(second, "token-secondary")

            await first.send_json({"type": "message", "content": "Only for room one."})
            await first.receive_json()

            assert await chat_registry.connection_count(other_room.id) == 1
            # Nothing was delivered to the other room's socket.
            with pytest.raises(TimeoutError):
                await second.receive_json(timeout=0.2)


async def test_history_written_before_the_socket_opened_is_readable(
    ws_app: FastAPI,
    api_client: AsyncClient,
    db_session: AsyncSession,
    debate_room: DebateRoom,
    user: User,
) -> None:
    """Reconnecting reads history over REST; the socket only carries what comes next."""
    await chat_service.post_message(db_session, debate_room.id, user, "Said earlier.")

    async with open_socket(ws_app, debate_room.id) as ws:
        await authenticate(ws, "token-primary")
        await ws.send_json({"type": "message", "content": "Said now."})
        await ws.receive_json()

    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/messages")

    assert [m["content"] for m in response.json()["messages"]] == ["Said earlier.", "Said now."]
