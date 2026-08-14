"""LiveKit token minting.

The grant carried by these tokens is the security boundary for video, so the tests decode
what was actually signed rather than trusting the SDK to have honoured the arguments.
"""

import uuid

import jwt
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.models import Topic, User
from app.services import match as match_service
from app.services import video as video_service
from tests.conftest import make_topic

API_KEY = "APItestkey"
API_SECRET = "test-secret-value-long-enough-to-sign-with"


@pytest.fixture
def video_settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        env="test",
        livekit_url="wss://test-project.livekit.cloud",
        livekit_api_key=API_KEY,
        livekit_api_secret=API_SECRET,
    )


@pytest.fixture
async def topic(db_session: AsyncSession, user: User) -> Topic:
    record = make_topic(user)
    db_session.add(record)
    await db_session.flush()
    return record


async def _matched_room_id(db_session: AsyncSession, user: User, other_user: User, topic: Topic):
    await match_service.join(db_session, other_user, topic.id)
    state = await match_service.join(db_session, user, topic.id)
    assert state.room is not None
    return state.room.id


def decode(token: str) -> dict:
    """Decode without verifying expiry, to inspect exactly what was granted."""
    return jwt.decode(token, API_SECRET, algorithms=["HS256"], options={"verify_aud": False})


async def test_a_participant_gets_a_token_for_their_room(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)

    result = await video_service.mint_room_token(db_session, room_id, user, video_settings)

    assert result.url == "wss://test-project.livekit.cloud"
    assert result.room_name == f"debate-{room_id}"
    assert result.token


async def test_the_grant_is_scoped_to_one_room_and_identity(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)

    result = await video_service.mint_room_token(db_session, room_id, user, video_settings)
    claims = decode(result.token)

    assert claims["sub"] == str(user.id), "identity must be the local user, not a client claim"
    grants = claims["video"]
    assert grants["room"] == f"debate-{room_id}"
    assert grants["roomJoin"] is True
    assert grants.get("canPublish") is True
    assert grants.get("canSubscribe") is True


async def test_the_grant_withholds_administrative_powers(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    """A leaked token must not be able to reach beyond its own debate."""
    room_id = await _matched_room_id(db_session, user, other_user, topic)

    claims = decode(
        (await video_service.mint_room_token(db_session, room_id, user, video_settings)).token
    )
    grants = claims["video"]

    for power in ("roomCreate", "roomAdmin", "roomList", "roomRecord", "ingressAdmin"):
        assert not grants.get(power), f"token should not grant {power}"


async def test_the_token_expires(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)

    claims = decode(
        (await video_service.mint_room_token(db_session, room_id, user, video_settings)).token
    )

    # The SDK stamps nbf/exp and no iat, so measure the validity window between those.
    lifetime = claims["exp"] - claims["nbf"]
    assert lifetime == video_settings.livekit_token_ttl_minutes * 60


async def test_both_debaters_get_distinct_identities_in_the_same_room(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)

    mine = decode(
        (await video_service.mint_room_token(db_session, room_id, user, video_settings)).token
    )
    theirs = decode(
        (await video_service.mint_room_token(db_session, room_id, other_user, video_settings)).token
    )

    assert mine["video"]["room"] == theirs["video"]["room"]
    assert mine["sub"] != theirs["sub"]


async def test_a_non_participant_is_refused(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)
    intruder = User(
        clerk_user_id="user_test_video_intruder",
        username="videointruder",
        email="videointruder@example.com",
    )
    db_session.add(intruder)
    await db_session.flush()

    with pytest.raises(PermissionDeniedError):
        await video_service.mint_room_token(db_session, room_id, intruder, video_settings)


async def test_an_ended_debate_issues_no_new_tokens(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic, video_settings: Settings
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)
    await match_service.end_room(db_session, room_id, user)

    with pytest.raises(ConflictError):
        await video_service.mint_room_token(db_session, room_id, user, video_settings)


async def test_an_unknown_room_is_not_found(
    db_session: AsyncSession, user: User, video_settings: Settings
) -> None:
    with pytest.raises(NotFoundError):
        await video_service.mint_room_token(db_session, uuid.uuid4(), user, video_settings)


async def test_minting_fails_closed_when_livekit_is_unconfigured(
    db_session: AsyncSession, user: User, other_user: User, topic: Topic
) -> None:
    room_id = await _matched_room_id(db_session, user, other_user, topic)
    unconfigured = Settings(_env_file=None, env="test")  # type: ignore[call-arg]

    with pytest.raises(Exception) as caught:
        await video_service.mint_room_token(db_session, room_id, user, unconfigured)

    assert "not configured" in str(caught.value)
