"""Post-debate rating model."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.debate_room import DebateRoom
    from app.models.user import User


class Rating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "ratings"
    __table_args__ = (
        # One rating per reviewer per room (enforced again in the Phase 8 service layer).
        UniqueConstraint("room_id", "reviewer_id", name="uq_ratings_room_reviewer"),
        CheckConstraint("score BETWEEN 1 AND 5", name="score_range"),
        CheckConstraint("reviewer_id <> reviewed_user_id", name="no_self_review"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("debate_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewed_user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    room: Mapped["DebateRoom"] = relationship(back_populates="ratings")
    reviewer: Mapped["User"] = relationship(foreign_keys=[reviewer_id])
    reviewed_user: Mapped["User"] = relationship(foreign_keys=[reviewed_user_id])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Rating id={self.id} score={self.score}>"
