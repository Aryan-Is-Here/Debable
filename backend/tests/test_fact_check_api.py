"""The fact-check endpoints, including the broadcast to both debaters.

Nothing here touches a network: the provider is overridden with a stub or a scripted double.
That is what keeps a 1,000-searches-a-month budget intact and the suite under ten seconds.
"""

import uuid

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import FactCheckProvider, FactCheckUnavailable, ProviderResult, ProviderSource
from app.ai.factory import get_fact_check_provider
from app.ai.stub import StubFactCheckProvider
from app.models import DebateRoom, User
from app.models.fact_check import FactCheckVerdict
from tests.conftest import make_topic
from tests.test_chat_socket import authenticate, open_socket

CLAIM = "The Great Depression began after a stock market crash."


class ScriptedProvider(FactCheckProvider):
    def __init__(self, result: ProviderResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    async def check(self, claim: str) -> ProviderResult:
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.fixture
def use_provider(app: FastAPI):
    """Install a provider for the duration of a test."""

    def _install(provider: FactCheckProvider) -> None:
        app.dependency_overrides[get_fact_check_provider] = lambda: provider

    _install(StubFactCheckProvider())
    return _install


async def test_a_participant_gets_a_verdict(
    api_client: AsyncClient, debate_room: DebateRoom, user: User, use_provider
) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": CLAIM}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["claim"] == CLAIM
    assert body["requesterId"] == str(user.id)
    assert body["verdict"] in {v.value for v in FactCheckVerdict}
    assert body["sources"]


async def test_a_verdict_appears_in_the_history(
    api_client: AsyncClient, debate_room: DebateRoom, use_provider
) -> None:
    await api_client.post(f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": CLAIM})

    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/fact-checks")

    assert response.status_code == 200
    assert [fc["claim"] for fc in response.json()["factChecks"]] == [CLAIM]


async def test_an_empty_history_is_an_empty_list(
    api_client: AsyncClient, debate_room: DebateRoom
) -> None:
    response = await api_client.get(f"/api/v1/rooms/{debate_room.id}/fact-checks")

    assert response.status_code == 200
    assert response.json() == {"factChecks": []}


async def test_a_claim_that_cannot_be_checked_is_a_503_and_stores_nothing(
    api_client: AsyncClient, debate_room: DebateRoom, use_provider
) -> None:
    """The phase's most important rule, at the HTTP boundary."""
    use_provider(ScriptedProvider(error=FactCheckUnavailable()))

    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": CLAIM}
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "fact_check_unavailable"

    history = await api_client.get(f"/api/v1/rooms/{debate_room.id}/fact-checks")
    assert history.json()["factChecks"] == []


async def test_the_daily_budget_returns_429(
    api_client: AsyncClient, app: FastAPI, debate_room: DebateRoom, use_provider
) -> None:
    from app.core.config import get_settings

    settings = app.dependency_overrides[get_settings]()
    original = settings.fact_check_daily_budget
    object.__setattr__(settings, "fact_check_daily_budget", 0)
    try:
        response = await api_client.post(
            f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": CLAIM}
        )
    finally:
        object.__setattr__(settings, "fact_check_daily_budget", original)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"


async def test_an_outsider_is_refused(
    api_client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    other_user: User,
    use_provider,
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
    # api_client is signed in as `user`, who is not in this room.
    room = DebateRoom(topic_id=topic.id, user1_id=other_user.id, user2_id=third.id)
    db_session.add(room)
    await db_session.flush()

    response = await api_client.post(f"/api/v1/rooms/{room.id}/fact-check", json={"claim": CLAIM})

    assert response.status_code == 403


async def test_an_unknown_room_is_404(api_client: AsyncClient, use_provider) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{uuid.uuid4()}/fact-check", json={"claim": CLAIM}
    )

    assert response.status_code == 404


async def test_a_short_claim_is_rejected(
    api_client: AsyncClient, debate_room: DebateRoom, use_provider
) -> None:
    response = await api_client.post(
        f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": "no"}
    )

    assert response.status_code == 422


async def test_a_verdict_is_broadcast_to_both_debaters(
    ws_app: FastAPI,
    api_client: AsyncClient,
    debate_room: DebateRoom,
    use_provider,
) -> None:
    """The check the phase exists to pass: the card appears on both sides, no refresh."""
    use_provider(
        ScriptedProvider(
            ProviderResult(
                verdict=FactCheckVerdict.TRUE,
                explanation="The sources agree.",
                sources=[
                    ProviderSource(
                        title="Wall Street crash of 1929",
                        url="https://en.wikipedia.org/wiki/Wall_Street_crash_of_1929",
                    )
                ],
            )
        )
    )

    async with open_socket(ws_app, debate_room.id) as first:
        await authenticate(first, "token-primary")
        async with open_socket(ws_app, debate_room.id) as second:
            await authenticate(second, "token-secondary")

            response = await api_client.post(
                f"/api/v1/rooms/{debate_room.id}/fact-check", json={"claim": CLAIM}
            )
            assert response.status_code == 200

            for socket in (first, second):
                frame = await socket.receive_json()
                assert frame["type"] == "fact_check"
                assert frame["factCheck"]["verdict"] == "true"
                assert frame["factCheck"]["sources"][0]["title"] == "Wall Street crash of 1929"
