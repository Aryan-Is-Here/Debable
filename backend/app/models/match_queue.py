"""Matchmaking queue.

One row per waiting user (enforced by the unique constraint on ``user_id``): a person can
only be looking for one debate at a time. Rows are deleted the moment a pair is formed, so
the table stays small — it is a queue, not a history.

Living in Postgres rather than process memory is deliberate. A deployed backend runs
several worker processes; per-process queues would leave two people waiting on the same
topic in separate queues, never to meet. See blueprint conflict #2.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.topic import Topic
    from app.models.user import User


class MatchQueueEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "match_queue"
    __table_args__ = (
        # Pairing reads "oldest waiter for this topic", so index the pair in that order.
        Index("ix_match_queue_topic_id_created_at", "topic_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        # Unique index rather than a bare constraint: a user has at most one place in the
        # queue, and lookups are always "is this user waiting?".
        unique=True,
        index=True,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Liveness heartbeat, refreshed by every status poll from the waiting room.
    #
    # A browser that closes gets no chance to withdraw: unload handlers are unreliable and
    # the request needs an auth token it has no time to fetch. So presence is proven by
    # continuing to poll rather than by promising to clean up. Entries that stop being
    # refreshed are ignored for matching and swept away — no ghost opponents.
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )

    user: Mapped["User"] = relationship()
    topic: Mapped["Topic"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<MatchQueueEntry user_id={self.user_id} topic_id={self.topic_id}>"
