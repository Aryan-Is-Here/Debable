"""Reporting a debater's conduct.

The test that matters most is ``test_a_live_debate_can_be_reported``: it is the one rule that
deliberately differs from ratings, and getting it wrong would mean telling someone being
harassed to wait until the debate is over.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.core.reports import REPORT_CATEGORIES
from app.models import DebateRoom, User
from app.services import report as report_service
from tests.conftest import make_topic

# --- Service ---------------------------------------------------------------------------


async def test_a_live_debate_can_be_reported(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    """The deliberate difference from ratings: harassment is reported as it happens."""
    assert debate_room.ended_at is None

    report = await report_service.submit(
        db_session, debate_room.id, user, category="Harassment", detail="Repeated slurs."
    )

    assert report.category == "Harassment"
    assert report.reporter_id == user.id
    assert report.reported_user_id == other_user.id


async def test_an_ended_debate_can_also_be_reported(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    debate_room.ended_at = datetime.now(UTC)
    await db_session.flush()

    report = await report_service.submit(
        db_session, debate_room.id, user, category="Spam", detail=None
    )

    assert report.detail is None


async def test_reporting_twice_is_refused(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """The same complaint filed five times should not read as five incidents."""
    # Captured before the failing call: the service's rollback expires session objects, and
    # these tests share one session where the application uses one per request.
    room_id = debate_room.id
    await report_service.submit(db_session, room_id, user, category="Spam", detail=None)

    with pytest.raises(ConflictError, match="already reported"):
        await report_service.submit(db_session, room_id, user, category="Threats", detail=None)


async def test_both_debaters_may_report_the_same_debate(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    """The constraint is per reporter, not per room — a mutual argument has two sides."""
    await report_service.submit(db_session, debate_room.id, user, category="Spam", detail=None)
    await report_service.submit(
        db_session, debate_room.id, other_user, category="Spam", detail=None
    )

    assert await report_service.has_reported(db_session, debate_room.id, user)
    assert await report_service.has_reported(db_session, debate_room.id, other_user)


async def test_a_non_participant_cannot_report(
    db_session: AsyncSession, debate_room: DebateRoom
) -> None:
    """Being in the room is what makes someone a witness — it is the basis for the report."""
    outsider = User(
        clerk_user_id="user_test_outsider",
        username="outsider",
        email="outsider@example.com",
        avatar_url=None,
    )
    db_session.add(outsider)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await report_service.submit(
            db_session, debate_room.id, outsider, category="Spam", detail=None
        )


async def test_an_unknown_room_is_not_found(db_session: AsyncSession, user: User) -> None:
    with pytest.raises(NotFoundError):
        await report_service.submit(db_session, uuid.uuid4(), user, category="Spam", detail=None)


async def test_has_reported_is_false_before_reporting(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    assert await report_service.has_reported(db_session, debate_room.id, user) is False


# --- API -------------------------------------------------------------------------------


async def test_a_participant_files_a_report(
    api_client: AsyncClient, debate_room: DebateRoom, other_user: User
) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/report",
        json={"category": "Hate speech", "detail": "Slurs in chat."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "Hate speech"
    assert body["reportedUserId"] == str(other_user.id)
    # No status field: there is no process behind a report in the MVP, and a status would
    # imply one.
    assert "status" not in body


async def test_a_blank_detail_is_stored_as_null(
    api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/report",
        json={"category": "Spam", "detail": "   "},
    )

    assert response.json()["detail"] is None


@pytest.mark.parametrize("category", REPORT_CATEGORIES)
async def test_every_listed_category_is_accepted(
    api_client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    other_user: User,
    category: str,
) -> None:
    """The allowlist and the column must agree — a category the UI offers must be storable."""
    topic = make_topic(user, title=f"A debate about {category} handling")
    db_session.add(topic)
    await db_session.flush()
    room = DebateRoom(topic_id=topic.id, user1_id=user.id, user2_id=other_user.id)
    db_session.add(room)
    await db_session.flush()

    response = await api_client.post(f"/api/v1/rooms/{room.id}/report", json={"category": category})

    assert response.status_code == 200, response.text


async def test_an_unknown_category_is_422(api_client: AsyncClient, debate_room: DebateRoom) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/report", json={"category": "Vibes"}
    )

    assert response.status_code == 422


async def test_an_overlong_detail_is_422(api_client: AsyncClient, debate_room: DebateRoom) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/report",
        json={"category": "Spam", "detail": "x" * 501},
    )

    assert response.status_code == 422


async def test_reporting_twice_is_409(api_client: AsyncClient, debate_room: DebateRoom) -> None:
    room_id = debate_room.id
    await api_client.post(f"/api/v1/rooms/{room_id}/report", json={"category": "Spam"})

    response = await api_client.post(
        f"/api/v1/rooms/{room_id}/report", json={"category": "Threats"}
    )

    assert response.status_code == 409


async def test_an_outsider_is_403(
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
    await db_session.flush()

    response = await api_client.post(f"/api/v1/rooms/{room.id}/report", json={"category": "Spam"})

    assert response.status_code == 403


async def test_reporting_requires_a_signed_in_caller(
    anonymous_api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await anonymous_api_client.post(
        f"/api/v1/rooms/{debate_room.id}/report", json={"category": "Spam"}
    )

    assert response.status_code == 401


async def test_there_is_no_endpoint_to_read_reports(
    api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    """Nothing in the MVP reads reports back, and no route should suggest otherwise."""
    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/report")

    assert response.status_code == 405
