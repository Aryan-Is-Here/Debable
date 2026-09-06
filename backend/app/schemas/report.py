"""Report request and response models."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import Field, field_validator

from app.core.reports import (
    REPORT_CATEGORIES,
    REPORT_DETAIL_MAX_LENGTH,
    is_valid_report_category,
)
from app.schemas.base import CamelModel

DetailStr = Annotated[str, Field(max_length=REPORT_DETAIL_MAX_LENGTH)]


class ReportCreate(CamelModel):
    """Payload for ``POST /rooms/{id}/report``."""

    category: str
    detail: DetailStr | None = None

    @field_validator("category")
    @classmethod
    def _known_category(cls, value: str) -> str:
        if not is_valid_report_category(value):
            allowed = ", ".join(REPORT_CATEGORIES)
            raise ValueError(f"Unknown category {value!r}. Allowed values: {allowed}.")
        return value

    @field_validator("detail", mode="before")
    @classmethod
    def _blank_is_none(cls, value: object) -> object:
        """An untouched textarea is "no detail", not an empty string."""
        if isinstance(value, str):
            return value.strip() or None
        return value


class ReportRead(CamelModel):
    """A filed report, returned only to the person who filed it.

    Carries no status field, because there is no process behind it — see
    ``app/models/report.py``.
    """

    id: uuid.UUID
    room_id: uuid.UUID
    reporter_id: uuid.UUID
    reported_user_id: uuid.UUID
    category: str
    detail: str | None
    created_at: datetime
