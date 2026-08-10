"""Topic request and response models.

Field names and bounds mirror ``frontend/lib/types.ts`` and
``frontend/lib/validation/topic.ts``. Those files are the contract: if a name changes here
without changing there, the Browse and Create screens break silently.
"""

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, field_validator

from app.core.categories import TOPIC_CATEGORIES
from app.models.topic import TopicStatus
from app.schemas.base import CamelModel
from app.schemas.user import UserSummary

# Bounds duplicated from the zod schema so a direct API call is held to the same rules as
# the form. Validation on only one side is worse than none — it teaches you to trust it.
TitleStr = Annotated[str, Field(min_length=10, max_length=120)]
DescriptionStr = Annotated[str, Field(min_length=20, max_length=600)]

TopicSortField = Literal["recent", "title"]


class TopicCreate(CamelModel):
    """Payload for ``POST /topics``."""

    title: TitleStr
    description: DescriptionStr
    category: str

    @field_validator("title", "description", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        """Trim before length checks, matching zod's ``.trim()`` ordering."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str) -> str:
        if value not in TOPIC_CATEGORIES:
            allowed = ", ".join(TOPIC_CATEGORIES)
            raise ValueError(f"Unknown category {value!r}. Allowed values: {allowed}.")
        return value


class TopicRead(CamelModel):
    """A topic as the UI renders it. Mirrors ``Topic`` in ``frontend/lib/types.ts``."""

    id: uuid.UUID
    title: str
    description: str
    category: str
    status: TopicStatus
    creator: UserSummary
    created_at: datetime

    # Number of people currently queued to debate this topic. There is no matchmaking queue
    # until Phase 4, so this is always 0 for now — kept in the response because the frontend
    # type already has it and removing it would force a UI change now and back again later.
    active_debaters: int = 0
