"""Chat message and WebSocket frame models.

The wire carries ``senderId`` rather than the frontend's viewer-relative
``author: "you" | "opponent" | "system"``. One broadcast frame reaches both debaters, and
"you" would mean the opposite thing on each side; the client maps the id against its own.

Frames are discriminated on ``type`` so a single ``TypeAdapter`` can parse whatever arrives
and reject anything unrecognised, rather than each handler poking at raw dictionaries.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator

from app.schemas.base import CamelModel

# An upper bound on one message. Generous for debate chat, but a bound the socket can rely
# on: without one, a single frame can be as large as the client cares to make it.
MAX_MESSAGE_LENGTH = 2000

MessageStr = Annotated[str, Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)]


class MessageRead(CamelModel):
    """One persisted chat message, as both the history endpoint and the socket send it."""

    id: uuid.UUID
    room_id: uuid.UUID
    sender_id: uuid.UUID
    content: str
    created_at: datetime


class MessageList(CamelModel):
    """A room's chat history, oldest first."""

    messages: list[MessageRead]


# --- Client -> server frames ------------------------------------------------------------


class AuthFrame(CamelModel):
    """The first frame every client must send. See ``app/websocket/auth.py``."""

    type: Literal["auth"]
    token: str


class SendMessageFrame(CamelModel):
    """A message the client wants persisted and broadcast."""

    type: Literal["message"]
    content: MessageStr

    @field_validator("content", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        """Trim before the length check, so whitespace alone is an empty message."""
        return value.strip() if isinstance(value, str) else value


ClientFrame = Annotated[AuthFrame | SendMessageFrame, Field(discriminator="type")]
client_frame_adapter: TypeAdapter[ClientFrame] = TypeAdapter(ClientFrame)


# --- Server -> client frames ------------------------------------------------------------


class ReadyFrame(CamelModel):
    """Sent once, after authentication succeeds. The client loads history on seeing it."""

    type: Literal["ready"] = "ready"
    room_id: uuid.UUID
    user_id: uuid.UUID


class MessageFrame(CamelModel):
    """A message broadcast to both debaters, including the one who sent it.

    The sender is echoed rather than trusted to render its own copy, so both windows show
    exactly what the server stored — one source of truth instead of optimistic state that
    can silently disagree with the database.
    """

    type: Literal["message"] = "message"
    message: MessageRead


class ErrorFrame(CamelModel):
    """A refusal that does not warrant closing the socket (an empty or over-long message).

    Reuses the ``code``/``message`` pair from the REST error envelope in ``core/errors.py``
    so clients handle one error shape across both transports.
    """

    type: Literal["error"] = "error"
    code: str
    message: str
