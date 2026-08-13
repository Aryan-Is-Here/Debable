"""Matchmaking endpoints over HTTP."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from tests.conftest import make_topic


async def _create_topic(db_session: AsyncSession, user: User) -> str:
    topic = make_topic(user)
    db_session.add(topic)
    await db_session.flush()
    return str(topic.id)


async def test_joining_the_queue_returns_queued(
    api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    topic_id = await _create_topic(db_session, user)

    response = await api_client.post("/api/v1/match", json={"topicId": topic_id})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["topic"]["id"] == topic_id
    assert body["queuedAt"] is not None
    assert body["waitingCount"] == 1


async def test_status_reflects_the_queue(
    api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    topic_id = await _create_topic(db_session, user)
    await api_client.post("/api/v1/match", json={"topicId": topic_id})

    response = await api_client.get("/api/v1/match")

    assert response.json()["status"] == "queued"


async def test_status_is_idle_before_queueing(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/match")

    assert response.status_code == 200
    assert response.json() == {
        "status": "idle",
        "topic": None,
        "queuedAt": None,
        "waitingCount": 0,
        "room": None,
    }


async def test_leaving_the_queue_returns_idle(
    api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    topic_id = await _create_topic(db_session, user)
    await api_client.post("/api/v1/match", json={"topicId": topic_id})

    response = await api_client.delete("/api/v1/match")

    assert response.status_code == 200
    assert response.json()["status"] == "idle"
    assert (await api_client.get("/api/v1/match")).json()["status"] == "idle"


async def test_anonymous_callers_cannot_queue(
    anonymous_api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    topic_id = await _create_topic(db_session, user)

    response = await anonymous_api_client.post("/api/v1/match", json={"topicId": topic_id})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_anonymous_callers_cannot_poll_status(
    anonymous_api_client: AsyncClient,
) -> None:
    assert (await anonymous_api_client.get("/api/v1/match")).status_code == 401


async def test_queueing_for_an_unknown_topic_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/match", json={"topicId": str(uuid.uuid4())})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_a_malformed_topic_id_returns_422(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/match", json={"topicId": "not-a-uuid"})

    assert response.status_code == 422


async def test_reading_an_unknown_room_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/rooms/{uuid.uuid4()}")

    assert response.status_code == 404


async def test_a_matched_pair_can_read_their_room(
    api_client: AsyncClient, db_session: AsyncSession, user: User, other_user: User
) -> None:
    from app.services import match as match_service

    topic_id = await _create_topic(db_session, user)
    # The opponent queues first, then the API caller joins and is paired with them.
    await match_service.join(db_session, other_user, uuid.UUID(topic_id))

    matched = (await api_client.post("/api/v1/match", json={"topicId": topic_id})).json()
    assert matched["status"] == "matched"

    room = await api_client.get(f"/api/v1/rooms/{matched['room']['id']}")

    assert room.status_code == 200
    body = room.json()
    assert body["you"]["id"] == str(user.id)
    assert body["opponent"]["id"] == str(other_user.id)
    assert body["endedAt"] is None
    assert "startedAt" in body


async def test_ending_a_debate_sets_the_end_time(
    api_client: AsyncClient, db_session: AsyncSession, user: User, other_user: User
) -> None:
    from app.services import match as match_service

    topic_id = await _create_topic(db_session, user)
    await match_service.join(db_session, other_user, uuid.UUID(topic_id))
    matched = (await api_client.post("/api/v1/match", json={"topicId": topic_id})).json()

    response = await api_client.post(f"/api/v1/rooms/{matched['room']['id']}/end")

    assert response.status_code == 200
    assert response.json()["endedAt"] is not None
    assert (await api_client.get("/api/v1/match")).json()["status"] == "idle"


async def test_waiting_count_appears_on_the_topic_list(
    api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    topic_id = await _create_topic(db_session, user)
    await api_client.post("/api/v1/match", json={"topicId": topic_id})

    listing = (await api_client.get("/api/v1/topics")).json()

    assert listing["items"][0]["activeDebaters"] == 1
