"""Close codes for the chat socket.

A refusal has to be legible to the client, and a WebSocket has only a close code to say it
with. The 4000–4999 range is reserved for applications, so each mirrors the HTTP status the
same refusal would produce over REST — 4401 for 401, 4403 for 403 — and a client can map
them with the same logic it already uses for ``ApiError.status``.

Only failures *before* the connection is ready close it. Once a debater is in, a refusal is
sent as an ``ErrorFrame`` and the socket stays open: mistyping an empty message should not
cost you the connection.
"""

from app.core.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_NOT_FOUND = 4404
CLOSE_CONFLICT = 4409
CLOSE_INTERNAL_ERROR = 4500

_BY_ERROR: dict[type[AppError], int] = {
    AuthenticationError: CLOSE_UNAUTHENTICATED,
    PermissionDeniedError: CLOSE_FORBIDDEN,
    NotFoundError: CLOSE_NOT_FOUND,
    ConflictError: CLOSE_CONFLICT,
}


def close_code_for(error: AppError) -> int:
    """The close code matching an application error, defaulting to a generic failure."""
    return _BY_ERROR.get(type(error), CLOSE_INTERNAL_ERROR)
