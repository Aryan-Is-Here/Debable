"""Report model — one participant reporting the other's conduct in a debate.

Resolves blueprint conflict #1: the PRD lists a Reports feature and
``docs/05-api-specification.md`` has ``POST /report``, but ``docs/04-database-design.md``
never had a table for it. This is the last schema gap in the project.

**A report is a record, not a workflow.** The MVP has no moderator and no moderation queue —
handbook §1 lists automatic moderation as out of scope — so there is deliberately no status
column, no assignee and no resolution. Adding them would imply a process that does not exist.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.reports import REPORT_CATEGORY_MAX_LENGTH
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.debate_room import DebateRoom
    from app.models.user import User


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        # One report per debate per reporter. Not because a second is harmful, but because
        # the same complaint filed five times should not read as five incidents.
        UniqueConstraint("room_id", "reporter_id", name="uq_reports_room_reporter"),
        # Short constraint name: the convention in `app/db/base.py` adds the `ck_` prefix,
        # and spelling it here would double it (§5.17).
        CheckConstraint("reporter_id <> reported_user_id", name="no_self_report"),
    )

    room_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("debate_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        # RESTRICT, unlike ratings: deleting an account must not erase reports made against
        # somebody else. A report outliving its reporter is the point of having one.
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    reported_user_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Validated against `app/core/reports.py` by the API schema, not by the database — see
    # that module for why this is not a Postgres enum.
    category: Mapped[str] = mapped_column(
        String(REPORT_CATEGORY_MAX_LENGTH), nullable=False, index=True
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    room: Mapped["DebateRoom"] = relationship(back_populates="reports")
    reporter: Mapped["User"] = relationship(foreign_keys=[reporter_id])
    reported_user: Mapped["User"] = relationship(foreign_keys=[reported_user_id])

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Report id={self.id} category={self.category}>"
