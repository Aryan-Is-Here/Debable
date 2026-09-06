"""Fact-check rules, without a model or a socket.

The two tests that matter most here are
``test_a_failed_check_is_not_recorded_as_unverified`` and
``test_a_verdict_with_no_trusted_sources_is_downgraded``. Everything else is ordinary
guarding; those two are the ones that decide whether the experiment's data means anything.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base import FactCheckProvider, FactCheckUnavailable, ProviderResult, ProviderSource
from app.ai.stub import StubFactCheckProvider
from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, RateLimitError
from app.models import DebateRoom, User
from app.models.fact_check import FactCheckVerdict
from app.services import fact_check as fact_check_service
from tests.conftest import make_topic

CLAIM = "A four-day week raises productivity."


class ScriptedProvider(FactCheckProvider):
    """Returns whatever the test says, or raises. Never touches a network."""

    def __init__(self, result: ProviderResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error
        self.calls: list[str] = []

    async def check(self, claim: str) -> ProviderResult:
        self.calls.append(claim)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "env": "test",
        "fact_check_rate_limit_per_hour": 10,
        "fact_check_daily_budget": 200,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


async def _request(
    db: AsyncSession,
    room: DebateRoom,
    user: User,
    *,
    provider: FactCheckProvider | None = None,
    settings: Settings | None = None,
    claim: str = CLAIM,
):
    return await fact_check_service.request_fact_check(
        db,
        room.id,
        user,
        claim,
        provider=provider or StubFactCheckProvider(),
        settings=settings or _settings(),
    )


# --- The happy path ---------------------------------------------------------------------


async def test_a_verdict_is_persisted_and_returned(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    result = await _request(db_session, debate_room, user)

    assert result.claim == CLAIM
    assert result.requester_id == user.id
    assert result.sources

    history = await fact_check_service.list_for_room(db_session, debate_room.id, user)
    assert [record.id for record in history] == [result.id]


async def test_only_the_claim_crosses_the_boundary(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """The isolation property doc 03 draws the AI as a separate box to guarantee."""
    provider = StubFactCheckProvider()

    await _request(db_session, debate_room, user, provider=provider)

    assert provider.calls == [CLAIM]


async def test_both_participants_read_the_same_history(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    await _request(db_session, debate_room, user)

    mine = await fact_check_service.list_for_room(db_session, debate_room.id, user)
    theirs = await fact_check_service.list_for_room(db_session, debate_room.id, other_user)

    assert [r.id for r in mine] == [r.id for r in theirs]


# --- The two rules that decide whether the data means anything --------------------------


async def test_a_failed_check_is_not_recorded_as_unverified(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """ "Never checked" must not become "checked and unresolved".

    If a provider failure were persisted as `unverified`, the dataset would fill with claims
    nobody examined, indistinguishable from real results and impossible to find later.
    """
    provider = ScriptedProvider(error=FactCheckUnavailable())

    with pytest.raises(FactCheckUnavailable):
        await _request(db_session, debate_room, user, provider=provider)

    history = await fact_check_service.list_for_room(db_session, debate_room.id, user)
    assert history == []


async def test_a_verdict_with_no_trusted_sources_is_downgraded(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """A confident verdict the debaters cannot check is the failure mode to avoid."""
    provider = ScriptedProvider(
        ProviderResult(
            verdict=FactCheckVerdict.TRUE,
            explanation="Definitely true, trust me.",
            sources=[ProviderSource(title="Some blog", url="https://blog.example.com/post")],
        )
    )

    result = await _request(db_session, debate_room, user, provider=provider)

    assert result.verdict == FactCheckVerdict.UNVERIFIED
    assert result.sources == []
    assert "trusted source" in result.explanation


async def test_untrusted_sources_are_stripped_but_trusted_ones_survive(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    provider = ScriptedProvider(
        ProviderResult(
            verdict=FactCheckVerdict.MISLEADING,
            explanation="Partly right.",
            sources=[
                ProviderSource(title="Random blog", url="https://blog.example.com/post"),
                ProviderSource(title="Reuters", url="https://www.reuters.com/article"),
            ],
        )
    )

    result = await _request(db_session, debate_room, user, provider=provider)

    assert result.verdict == FactCheckVerdict.MISLEADING
    assert [source.title for source in result.sources] == ["Reuters"]


async def test_a_redirect_url_is_judged_on_its_domain_field(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """Gemini returns redirect URIs; filtering on the URL would discard every citation."""
    provider = ScriptedProvider(
        ProviderResult(
            verdict=FactCheckVerdict.TRUE,
            explanation="Backed by the BLS.",
            sources=[
                ProviderSource(
                    title="Bureau of Labor Statistics",
                    url="https://vertexaisearch.cloud.google.com/grounding-api-redirect/abc123",
                    domain="bls.gov",
                )
            ],
        )
    )

    result = await _request(db_session, debate_room, user, provider=provider)

    assert result.verdict == FactCheckVerdict.TRUE
    assert len(result.sources) == 1
    # The redirect is what gets stored — it resolves, and it is what the provider gave us.
    assert result.sources[0].url.startswith("https://vertexaisearch.cloud.google.com/")


async def test_an_unverified_verdict_survives_without_sources(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """`unverified` with nothing to cite is a legitimate answer, not a downgrade."""
    provider = ScriptedProvider(
        ProviderResult(
            verdict=FactCheckVerdict.UNVERIFIED,
            explanation="Nothing settles this.",
            sources=[],
        )
    )

    result = await _request(db_session, debate_room, user, provider=provider)

    assert result.verdict == FactCheckVerdict.UNVERIFIED
    assert result.explanation == "Nothing settles this."


# --- Access and lifecycle ---------------------------------------------------------------


async def test_a_non_participant_cannot_request(
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
        await _request(db_session, debate_room, outsider)


async def test_an_unknown_room_is_not_found(db_session: AsyncSession, user: User) -> None:
    with pytest.raises(NotFoundError):
        await fact_check_service.request_fact_check(
            db_session,
            uuid.uuid4(),
            user,
            CLAIM,
            provider=StubFactCheckProvider(),
            settings=_settings(),
        )


async def test_an_ended_debate_refuses_new_checks(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    debate_room.ended_at = datetime.now(UTC)
    await db_session.flush()

    with pytest.raises(ConflictError):
        await _request(db_session, debate_room, user)


async def test_an_ended_debate_is_still_readable(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    await _request(db_session, debate_room, user)
    debate_room.ended_at = datetime.now(UTC)
    await db_session.flush()

    history = await fact_check_service.list_for_room(db_session, debate_room.id, user)

    assert len(history) == 1


# --- Rate limits ------------------------------------------------------------------------


async def test_the_room_limit_stops_one_debate_spamming(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    settings = _settings(fact_check_rate_limit_per_hour=2)

    for _ in range(2):
        await _request(db_session, debate_room, user, settings=settings)

    with pytest.raises(RateLimitError, match="fact-checks"):
        await _request(db_session, debate_room, user, settings=settings)


async def test_the_daily_budget_protects_the_shared_quota(
    db_session: AsyncSession, debate_room: DebateRoom, user: User, other_user: User
) -> None:
    """A per-room limit cannot defend a global quota, because rooms cannot see each other."""
    settings = _settings(fact_check_rate_limit_per_hour=50, fact_check_daily_budget=2)

    for _ in range(2):
        await _request(db_session, debate_room, user, settings=settings)

    # A different room, well under its own hourly limit, is still refused.
    topic = make_topic(user, title="A separate debate about something else")
    db_session.add(topic)
    await db_session.flush()
    other_room = DebateRoom(topic_id=topic.id, user1_id=user.id, user2_id=other_user.id)
    db_session.add(other_room)
    await db_session.flush()

    with pytest.raises(RateLimitError, match="daily limit"):
        await _request(db_session, other_room, user, settings=settings)


async def test_a_refused_request_does_not_call_the_provider(
    db_session: AsyncSession, debate_room: DebateRoom, user: User
) -> None:
    """The limit exists to save quota, so it has to run before the request is made."""
    settings = _settings(fact_check_daily_budget=0)
    provider = StubFactCheckProvider()

    with pytest.raises(RateLimitError):
        await _request(db_session, debate_room, user, provider=provider, settings=settings)

    assert provider.calls == []
