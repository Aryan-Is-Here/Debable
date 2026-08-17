"""LiveKit access tokens for debate rooms.

The browser never sees the LiveKit API secret. It asks this service for a token, which is
signed here and scoped so narrowly that leaking one grants access to a single room, as a
single identity, for a bounded time.

The grant is the security boundary, so it is deliberately minimal: join one named room,
publish and subscribe within it, and nothing else. No room creation, no admin, no listing.
"""

import logging
import uuid
from datetime import timedelta

from livekit.api import AccessToken, VideoGrants
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.errors import ConflictError, NotFoundError, ServiceUnavailableError
from app.models.user import User
from app.repositories import match as match_repo
from app.schemas.video import RoomToken
from app.services.match import to_room_read

logger = logging.getLogger(__name__)


def room_name_for(room_id: uuid.UUID) -> str:
    """LiveKit's room name for a debate. The debate room id, one to one."""
    return f"debate-{room_id}"


async def mint_room_token(
    db: AsyncSession, room_id: uuid.UUID, user: User, settings: Settings
) -> RoomToken:
    """Issue a LiveKit token for one participant of one debate.

    Raises ``NotFoundError`` for an unknown room, ``PermissionDeniedError`` for anyone who
    is not one of its two debaters, and ``ConflictError`` once the debate has ended — a
    finished debate should not hand out fresh media credentials.
    """
    if not settings.livekit_configured:
        # Fail closed and say why, rather than minting a token nobody can use.
        raise ServiceUnavailableError("Video is not configured on this server.")

    room = await match_repo.get_room(db, room_id)
    if room is None:
        raise NotFoundError("Debate room not found.")

    # Reuses the participant check that already guards room reads: raises for outsiders.
    to_room_read(room, user.id)

    if room.ended_at is not None:
        raise ConflictError("This debate has ended.")

    grants = VideoGrants(
        room_join=True,
        room=room_name_for(room_id),
        can_publish=True,
        can_subscribe=True,
        # Chat rides its own transport in Phase 6; no need for LiveKit data channels.
        can_publish_data=False,
    )

    token = (
        AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
        # Identity is the local user id, so tracks can be attributed to a known debater
        # rather than to whatever name a client claims.
        .with_identity(str(user.id))
        .with_name(user.username)
        .with_ttl(timedelta(minutes=settings.livekit_token_ttl_minutes))
        .with_grants(grants)
        .to_jwt()
    )

    logger.info(
        "Minted LiveKit token",
        extra={"room_id": str(room_id), "user_id": str(user.id)},
    )
    return RoomToken(url=settings.livekit_url, token=token, room_name=room_name_for(room_id))
