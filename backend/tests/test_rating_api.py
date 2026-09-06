"""Rating and profile endpoints over HTTP."""

import uuid
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DebateRoom, User
from app.services import rating as rating_service
from tests.conftest import make_topic


async def _end(db: AsyncSession, room: DebateRoom) -> None:
    room.ended_at = datetime.now(UTC)
    await db.flush()


async def test_a_participant_rates_after_the_debate(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom, other_user: User
) -> None:
    await _end(db_session, debate_room)

    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/rating",
        json={"score": 5, "comment": "Sharp and fair."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 5
    assert body["comment"] == "Sharp and fair."
    # camelCase on the wire, matching frontend/lib/types.ts.
    assert body["reviewedUserId"] == str(other_user.id)


async def test_a_blank_comment_is_stored_as_null(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    """An empty textarea is "no comment", not an empty comment."""
    await _end(db_session, debate_room)

    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/rating", json={"score": 3, "comment": "   "}
    )

    assert response.json()["comment"] is None


async def test_rating_twice_is_409(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    await _end(db_session, debate_room)
    room_id = debate_room.id
    await api_client.post(f"/api/v1/rooms/{room_id}/rating", json={"score": 5})

    response = await api_client.post(f"/api/v1/rooms/{room_id}/rating", json={"score": 1})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_rating_an_unfinished_debate_is_409(
    api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await api_client.post(f"/api/v1/rooms/{debate_room.id}/rating", json={"score": 5})

    assert response.status_code == 409


async def test_a_score_outside_one_to_five_is_422(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    await _end(db_session, debate_room)

    for score in (0, 6, -1):
        response = await api_client.post(
            f"/api/v1/rooms/{debate_room.id}/rating", json={"score": score}
        )
        assert response.status_code == 422, score


async def test_an_overlong_comment_is_422(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    await _end(db_session, debate_room)

    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/rating",
        json={"score": 4, "comment": "x" * 301},
    )

    assert response.status_code == 422


async def test_an_outsider_is_refused(
    api_client: AsyncClient, db_session: AsyncSession, user: User, other_user: User
) -> None:
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
    # api_client is signed in as `user`, who was not in this debate.
    room = DebateRoom(topic_id=topic.id, user1_id=other_user.id, user2_id=third.id)
    db_session.add(room)
    await _end(db_session, room)

    response = await api_client.post(f"/api/v1/rooms/{room.id}/rating", json={"score": 5})

    assert response.status_code == 403


async def test_an_unknown_room_is_404(api_client: AsyncClient) -> None:
    response = await api_client.post(f"/api/v1/rooms/{uuid.uuid4()}/rating", json={"score": 5})

    assert response.status_code == 404


async def test_rating_requires_a_signed_in_caller(
    anonymous_api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await anonymous_api_client.post(
        f"/api/v1/rooms/{debate_room.id}/rating", json={"score": 5}
    )

    assert response.status_code == 401


async def test_the_state_endpoint_reports_whether_you_rated(
    api_client: AsyncClient, db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    await _end(db_session, debate_room)
    room_id = debate_room.id

    before = await api_client.get(f"/api/v1/rooms/{room_id}/rating")
    assert before.json() == {"submitted": False, "rating": None}

    await api_client.post(f"/api/v1/rooms/{room_id}/rating", json={"score": 2})

    after = await api_client.get(f"/api/v1/rooms/{room_id}/rating")
    assert after.json()["submitted"] is True
    assert after.json()["rating"]["score"] == 2


# --- Profile ---------------------------------------------------------------------------


async def test_an_empty_profile_reports_no_average(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/profile")

    assert response.status_code == 200
    body = response.json()
    assert body["debatesCount"] == 0
    assert body["averageRating"] is None
    assert body["history"] == []
    assert body["joinedAt"]


async def test_the_profile_reflects_a_finished_rated_debate(
    api_client: AsyncClient,
    db_session: AsyncSession,
    debate_room: DebateRoom,
    user: User,
    other_user: User,
) -> None:
    await _end(db_session, debate_room)
    # The opponent rates `user`, who is the signed-in caller.
    await rating_service.submit(db_session, debate_room.id, other_user, score=4, comment=None)

    response = await api_client.get("/api/v1/profile")

    body = response.json()
    assert body["debatesCount"] == 1
    assert body["averageRating"] == 4.0
    assert body["history"][0]["ratingReceived"] == 4
    assert body["history"][0]["opponent"]["id"] == str(other_user.id)


async def test_the_profile_requires_a_signed_in_caller(
    anonymous_api_client: AsyncClient,
) -> None:
    response = await anonymous_api_client.get("/api/v1/profile")

    assert response.status_code == 401
