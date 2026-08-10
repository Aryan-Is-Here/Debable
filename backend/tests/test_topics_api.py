"""Topic endpoints over HTTP."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.categories import TOPIC_CATEGORIES
from app.models import User
from tests.conftest import make_topic

VALID_PAYLOAD = {
    "title": "Should university tuition be free",
    "description": "Debating whether higher education should be funded entirely by the state.",
    "category": "Education",
}


async def test_create_returns_201_with_the_created_topic(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == VALID_PAYLOAD["title"]
    assert body["category"] == "Education"
    assert body["status"] == "open"
    assert body["creator"]["username"] == "debater"


async def test_response_uses_the_camelcase_shape_the_frontend_expects(
    api_client: AsyncClient,
) -> None:
    body = (await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)).json()

    assert "createdAt" in body
    assert "activeDebaters" in body
    assert "avatarUrl" in body["creator"]
    assert "created_at" not in body


async def test_creator_email_is_never_exposed(api_client: AsyncClient) -> None:
    body = (await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)).json()

    assert "email" not in body["creator"]


async def test_anonymous_callers_cannot_create_topics(
    anonymous_api_client: AsyncClient,
) -> None:
    response = await anonymous_api_client.post("/api/v1/topics", json=VALID_PAYLOAD)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_anonymous_callers_can_browse(
    anonymous_api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    db_session.add(make_topic(user))
    await db_session.flush()

    response = await anonymous_api_client.get("/api/v1/topics")

    assert response.status_code == 200
    assert response.json()["total"] == 1


async def test_a_title_that_is_too_short_is_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post("/api/v1/topics", json={**VALID_PAYLOAD, "title": "Too short"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_a_description_that_is_too_long_is_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/topics", json={**VALID_PAYLOAD, "description": "x" * 601}
    )

    assert response.status_code == 422


async def test_an_unknown_category_is_rejected(api_client: AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/topics", json={**VALID_PAYLOAD, "category": "Astrology"}
    )

    assert response.status_code == 422
    # A custom validator's ValueError must survive serialisation into the error envelope.
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "Astrology" in str(body["error"]["details"])


async def test_surrounding_whitespace_is_trimmed_before_validation(
    api_client: AsyncClient,
) -> None:
    response = await api_client.post(
        "/api/v1/topics",
        json={**VALID_PAYLOAD, "title": f"   {VALID_PAYLOAD['title']}   "},
    )

    assert response.status_code == 201
    assert response.json()["title"] == VALID_PAYLOAD["title"]


async def test_duplicate_title_returns_409(api_client: AsyncClient) -> None:
    await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)

    response = await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_created_topic_survives_a_fresh_request(api_client: AsyncClient) -> None:
    """The persistence check: create, then read back through a separate request."""
    created = (await api_client.post("/api/v1/topics", json=VALID_PAYLOAD)).json()

    fetched = await api_client.get(f"/api/v1/topics/{created['id']}")

    assert fetched.status_code == 200
    assert fetched.json()["id"] == created["id"]


async def test_unknown_topic_id_returns_404(api_client: AsyncClient) -> None:
    response = await api_client.get(f"/api/v1/topics/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_malformed_topic_id_returns_422(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/topics/not-a-uuid")

    assert response.status_code == 422


async def test_search_and_category_are_applied_by_the_endpoint(
    api_client: AsyncClient, db_session: AsyncSession, user: User
) -> None:
    db_session.add_all(
        [
            make_topic(user, title="Voting age should be lowered", category="Politics"),
            make_topic(user, title="Voting machines and trust", category="Technology"),
        ]
    )
    await db_session.flush()

    response = await api_client.get(
        "/api/v1/topics", params={"search": "voting", "category": "Politics"}
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Voting age should be lowered"


async def test_limit_above_the_cap_is_rejected(api_client: AsyncClient) -> None:
    response = await api_client.get("/api/v1/topics", params={"limit": 500})

    assert response.status_code == 422


async def test_categories_endpoint_lists_the_allowlist(anonymous_api_client: AsyncClient) -> None:
    response = await anonymous_api_client.get("/api/v1/topics/categories")

    assert response.status_code == 200
    assert response.json() == list(TOPIC_CATEGORIES)
