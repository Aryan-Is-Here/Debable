"""Matchmaking request and response models."""

import enum
import uuid
from datetime import datetime

from app.schemas.base import CamelModel
from app.schemas.topic import TopicRead
from app.schemas.user import UserSummary


class MatchStatus(enum.StrEnum):
    """What the caller is currently doing."""

    IDLE = "idle"
    """Neither queued nor in a room."""

    QUEUED = "queued"
    """Waiting for an opponent."""

    MATCHED = "matched"
    """Paired — ``room`` is populated."""


class MatchRequest(CamelModel):
    """Payload for joining the queue."""

    topic_id: uuid.UUID


class DebateRoomRead(CamelModel):
    """A debate room. Mirrors ``DebateRoom`` in ``frontend/lib/types.ts``.

    ``you`` and ``opponent`` are resolved per caller rather than exposing user1/user2, so
    the UI never has to work out which side it is on.
    """

    id: uuid.UUID
    topic: TopicRead
    you: UserSummary
    opponent: UserSummary
    started_at: datetime
    ended_at: datetime | None = None


class MatchState(CamelModel):
    """The polled matchmaking state."""

    status: MatchStatus
    topic: TopicRead | None = None
    """The topic being queued for, when status is ``queued``."""

    queued_at: datetime | None = None
    """When the caller joined the queue, so the UI can show elapsed time."""

    waiting_count: int = 0
    """How many people are queued for this topic, including the caller."""

    room: DebateRoomRead | None = None
    """The debate room, when status is ``matched``."""
