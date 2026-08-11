"""Debate room model — one 1v1 session on a topic."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.fact_check import FactCheck
    from app.models.message import Message
    from app.models.rating import Rating
    from app.models.topic import Topic
    from app.models.user import User


class DebateRoom(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "debate_rooms"
    __table_args__ = (
        # A user cannot debate themselves; matchmaking (Phase 4) must pair distinct users.
        CheckConstraint("user1_id <> user2_id", name="distinct_users"),
    )

    topic_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user1_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    user2_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # NULL while the debate is live; set when either participant ends it.
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    topic: Mapped["Topic"] = relationship(back_populates="rooms")
    # Two foreign keys to the same table, so each side must say which one it follows.
    user1: Mapped["User"] = relationship(foreign_keys=[user1_id])
    user2: Mapped["User"] = relationship(foreign_keys=[user2_id])
    messages: Mapped[list["Message"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    fact_checks: Mapped[list["FactCheck"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )
    ratings: Mapped[list["Rating"]] = relationship(
        back_populates="room", cascade="all, delete-orphan"
    )

    @property
    def is_active(self) -> bool:
        return self.ended_at is None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<DebateRoom id={self.id} topic_id={self.topic_id}>"
