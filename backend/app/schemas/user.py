"""User response models."""

import uuid

from app.schemas.base import CamelModel


class UserSummary(CamelModel):
    """Public-safe user fields. Mirrors ``UserSummary`` in the frontend's ``lib/types.ts``.

    Deliberately excludes email: this is embedded in every topic and every debate room, and
    a debater's address is not public information.
    """

    id: uuid.UUID
    username: str
    avatar_url: str | None = None
