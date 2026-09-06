"""Fact-check request and response models.

Mirrors ``FactCheck`` and ``FactCheckSource`` in ``frontend/lib/types.ts``, which the
`FactCheckCard` component already renders — the UI for this phase largely exists, it has
been drawing mock data since Phase 1.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from app.models.fact_check import FactCheckVerdict
from app.schemas.base import CamelModel

# Long enough for a real claim with its qualifiers, short enough that nobody pastes an essay
# into a shared daily quota. The lower bound rejects "true?" and similar non-claims.
ClaimStr = Annotated[str, Field(min_length=10, max_length=500)]


class FactCheckRequest(CamelModel):
    """Payload for ``POST /rooms/{id}/fact-check``."""

    claim: ClaimStr

    @field_validator("claim", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class FactCheckSource(CamelModel):
    """One citation shown beneath a verdict."""

    title: str
    url: str


class FactCheckRead(CamelModel):
    """A verdict as the UI renders it."""

    id: uuid.UUID
    room_id: uuid.UUID
    requester_id: uuid.UUID
    claim: str
    verdict: FactCheckVerdict
    explanation: str
    sources: list[FactCheckSource]
    created_at: datetime


class FactCheckList(CamelModel):
    """A room's fact-checks, oldest first."""

    fact_checks: list[FactCheckRead]
