"""FastAPI dependencies for authenticated routes.

``get_current_claims`` verifies the bearer token only. ``get_current_user`` additionally
resolves — and on first sight creates — the local ``users`` row Clerk's subject maps to.

The resolution step lives in the plain ``resolve_user`` function rather than the dependency
itself, because a WebSocket handshake authenticates from a frame rather than a header and
must reach the same provisioning logic without going through FastAPI's dependency system.
"""

import logging
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.clerk import ClerkTokenVerifier, ClerkUser, get_token_verifier
from app.core.errors import AuthenticationError
from app.db.session import get_db
from app.models import User

logger = logging.getLogger(__name__)

# auto_error=False so a missing header raises our AuthenticationError (uniform error body)
# rather than FastAPI's default 403.
_bearer_scheme = HTTPBearer(auto_error=False, description="Clerk-issued session JWT")

BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]
Verifier = Annotated[ClerkTokenVerifier, Depends(get_token_verifier)]
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_claims(credentials: BearerToken, verifier: Verifier) -> ClerkUser:
    """Verify the ``Authorization: Bearer <jwt>`` header and return its claims."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token.")
    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Authorization scheme must be Bearer.")
    return await verifier.verify(credentials.credentials)


async def get_optional_claims(credentials: BearerToken, verifier: Verifier) -> ClerkUser | None:
    """Same as ``get_current_claims`` but returns ``None`` for anonymous callers.

    For endpoints that show more to a signed-in user but do not require one.
    """
    if credentials is None or not credentials.credentials:
        return None
    return await verifier.verify(credentials.credentials)


async def resolve_user(db: AsyncSession, claims: ClerkUser) -> User:
    """Return the local ``users`` row for a verified subject, creating it if absent.

    Clerk is the identity source; this table exists so debates, topics and ratings have
    something to foreign-key. Provisioning lazily on first authenticated request keeps
    Phase 2 free of a webhook receiver (that can replace this later without touching
    call sites).
    """
    existing = await db.scalar(select(User).where(User.clerk_user_id == claims.clerk_user_id))
    if existing is not None:
        return existing

    user = User(
        clerk_user_id=claims.clerk_user_id,
        username=claims.fallback_username,
        email=claims.email or f"{claims.clerk_user_id}@users.noreply.clerk",
        avatar_url=claims.avatar_url,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        # Concurrent first requests race to insert; whoever lost re-reads the winner's row.
        await db.rollback()
        existing = await db.scalar(select(User).where(User.clerk_user_id == claims.clerk_user_id))
        if existing is None:
            raise
        return existing

    await db.refresh(user)
    logger.info("Provisioned user from Clerk", extra={"clerk_user_id": claims.clerk_user_id})
    return user


async def get_current_user(
    claims: Annotated[ClerkUser, Depends(get_current_claims)],
    db: DbSession,
) -> User:
    """The signed-in caller, as a dependency. See ``resolve_user``."""
    return await resolve_user(db, claims)


CurrentClaims = Annotated[ClerkUser, Depends(get_current_claims)]
CurrentUser = Annotated[User, Depends(get_current_user)]
