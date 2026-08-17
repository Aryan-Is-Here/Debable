"""The chat history endpoint over HTTP.

History is REST precisely so it can be tested — and read by a client — without a working
socket. These are the cases that prove it enforces the same access rule as the room itself.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DebateRoom, User
from app.services import chat as chat_service
from tests.conftest import make_topic


async def test_a_participant_reads_the_history(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    await chat_service.post_message(db_session, debate_room.id, user, "On the record.")

    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/messages")

    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 1
    # camelCase on the wire, matching ChatMessage in frontend/lib/types.ts.
    assert messages[0]["content"] == "On the record."
    assert messages[0]["senderId"] == str(user.id)
    assert messages[0]["roomId"] == str(debate_room.id)
    assert messages[0]["createdAt"]


async def test_an_empty_room_returns_an_empty_list(
    api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/messages")

    assert response.status_code == 200
    assert response.json() == {"messages": []}


async def test_an_outsider_is_refused(
    api_client: AsyncClient, db_session: AsyncSession, user: User, other_user: User
) -> None:
    """A room between two other people is invisible, exactly as GET /rooms/{id} is."""
    third = User(
        clerk_user_id="user_test_third",
        username="third",
        email="third@example.com",
        avatar_url=None,
    )
    db_session.add(third)
    await db_session.flush()

    topic = make_topic(other_user)
    db_session.add(topic)
    await db_session.flush()
    # api_client is signed in as `user`, who is not in this room.
    room = DebateRoom(topic_id=topic.id, user1_id=other_user.id, user2_id=third.id)
    db_session.add(room)
    await db_session.flush()

    response = await api_client.get(f"/api/v1/rooms/{room.id}/messages")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_an_unknown_room_is_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/rooms/{uuid.uuid4()}/messages")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_history_requires_a_signed_in_caller(
    anonymous_api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await anonymous_api_client.get(f"/api/v1/rooms/{debate_room.id}/messages")

    assert response.status_code == 401
