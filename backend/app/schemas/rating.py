"""Post-debate rating models.

Mirrors `RatingForm` in `frontend/components/rating-form.tsx`, which has rendered this shape
since Phase 1 — 1–5 stars and an optional comment.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from app.schemas.base import CamelModel
from app.schemas.user import UserSummary

# Duplicated from the form's own bound so a direct API call is held to the same rule. The
# score bounds are additionally a CHECK constraint in the database — see app/models/rating.py.
CommentStr = Annotated[str, Field(max_length=300)]
ScoreInt = Annotated[int, Field(ge=1, le=5)]


class RatingCreate(CamelModel):
    """Payload for ``POST /rooms/{id}/rating``."""

    score: ScoreInt
    comment: CommentStr | None = None

    @field_validator("comment", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        """An empty textarea is "no comment", not an empty comment."""
        if isinstance(value, str):
            trimmed = value.strip()
            return trimmed or None
        return value


class RatingRead(CamelModel):
    """One rating, as returned to the person who left it."""

    id: uuid.UUID
    room_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewed_user_id: uuid.UUID
    score: int
    comment: str | None
    created_at: datetime


class RatingState(CamelModel):
    """Whether the caller has already rated this debate.

    The results screen asks before rendering the form: an accidental second visit should show
    what was submitted, not an empty form that will be refused on submit.
    """

    submitted: bool
    rating: RatingRead | None = None


class DebateHistoryEntry(CamelModel):
    """One finished debate, as the profile lists it.

    Mirrors ``DebateHistoryEntry`` in ``frontend/lib/types.ts``.
    """

    id: uuid.UUID
    topic_title: str
    opponent: UserSummary
    rating_received: int | None = None
    date: datetime


class UserProfileRead(CamelModel):
    """The profile screen's data. Mirrors ``UserProfile`` in ``frontend/lib/types.ts``."""

    user: UserSummary
    joined_at: datetime
    debates_count: int
    average_rating: float | None = None
    """``None`` until somebody has rated this user.

    Nullable rather than defaulting to a number, because there is no honest number for "not
    yet rated" — a 0 reads as terrible and a 5 is a lie. The UI has an empty state for it.
    """

    history: list[DebateHistoryEntry]
