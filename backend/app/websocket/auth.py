"""Authenticating a WebSocket connection.

A browser ``WebSocket`` cannot set an ``Authorization`` header, so the token arrives in the
first frame instead. The alternative — a token in the query string — was rejected because a
Clerk session JWT would then sit in access logs, proxy logs and browser history.

The cost of authenticating from a frame is that the socket must be accepted before anything
can be read from it, so an unauthenticated connection exists briefly. ``AUTH_TIMEOUT_SECONDS``
bounds that: a client that connects and says nothing is closed rather than parked.

Verification itself is *not* reimplemented here. ``ClerkTokenVerifier`` and ``resolve_user``
are the same ones the HTTP dependencies use, so there is one way to decide who a caller is.
"""

import asyncio
import logging

from fastapi import WebSocket

from app.auth.clerk import ClerkTokenVerifier
from app.auth.dependencies import resolve_user
from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.db.session import SessionScope
from app.models.user import User
from app.schemas.chat import AuthFrame, client_frame_adapter

logger = logging.getLogger(__name__)

# How long a freshly accepted socket may stay silent before it is closed. Long enough for a
# client to send a frame it already has in hand, short enough that idle sockets cannot pile
# up.
AUTH_TIMEOUT_SECONDS = 5.0


def origin_allowed(websocket: WebSocket, settings: Settings) -> bool:
    """Whether this handshake's ``Origin`` is one we serve.

    Necessary because **CORS does not apply to WebSockets**: the ``CORSMiddleware`` in
    ``app/main.py`` never sees a handshake, so ``cors_origins`` would otherwise constrain
    the REST API and nothing else. This is defence in depth rather than the access control
    — the token frame is what actually authenticates — so a request with no ``Origin`` at
    all is allowed through: that is a non-browser client, which could equally send any
    origin it liked.
    """
    origin = websocket.headers.get("origin")
    if origin is None:
        return True
    return origin in settings.cors_origins


async def authenticate_socket(
    websocket: WebSocket, verifier: ClerkTokenVerifier, scope: SessionScope
) -> User:
    """Read the first frame, verify its token, and return the caller's local user row.

    Raises ``AuthenticationError`` if the frame never arrives, is not an ``auth`` frame, or
    carries a token that does not verify.
    """
    try:
        raw = await asyncio.wait_for(websocket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS)
    except TimeoutError:
        raise AuthenticationError("Timed out waiting for authentication.") from None
    except (ValueError, TypeError):
        # receive_json raises when the payload is not JSON at all.
        raise AuthenticationError("Malformed authentication frame.") from None

    try:
        frame = client_frame_adapter.validate_python(raw)
    except Exception:  # noqa: BLE001 - pydantic's ValidationError, reported as a refusal
        raise AuthenticationError("Malformed authentication frame.") from None

    if not isinstance(frame, AuthFrame):
        raise AuthenticationError("The first frame must be an auth frame.")

    claims = await verifier.verify(frame.token)
    async with scope() as db:
        return await resolve_user(db, claims)
