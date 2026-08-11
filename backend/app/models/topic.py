"""Debate topic model."""

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.categories import CATEGORY_MAX_LENGTH
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.debate_room import DebateRoom
    from app.models.user import User


class TopicStatus(enum.StrEnum):
    """Lifecycle of a topic. Mirrors ``TopicStatus`` in the frontend's ``lib/types.ts``."""

    OPEN = "open"
    ACTIVE = "active"
    ARCHIVED = "archived"


class Topic(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "topics"

    # Bounds match the frontend zod schema in `frontend/lib/validation/topic.ts`.
    title: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Deliberately a plain string with no CHECK constraint — the allowed values live in
    # app.core.categories and are enforced by the API schema. See that module for why.
    category: Mapped[str] = mapped_column(String(CATEGORY_MAX_LENGTH), nullable=False, index=True)
    status: Mapped[TopicStatus] = mapped_column(
        SAEnum(TopicStatus, name="topic_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=TopicStatus.OPEN,
        server_default=TopicStatus.OPEN.value,
        index=True,
    )

    creator: Mapped["User"] = relationship(back_populates="created_topics")
    rooms: Mapped[list["DebateRoom"]] = relationship(back_populates="topic")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Topic id={self.id} title={self.title!r}>"
