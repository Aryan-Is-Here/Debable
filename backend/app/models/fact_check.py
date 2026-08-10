"""Fact-check model — the result of one on-demand AI verification request.

``sources`` is JSONB (blueprint conflict #4): a list of ``{"title": ..., "url": ...}``
objects matching ``FactCheckSource`` in the frontend's ``lib/types.ts``. JSONB rather than
a side table because sources are never queried independently — they are always rendered
with their verdict.
"""

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.debate_room import DebateRoom
    from app.models.user import User


class FactCheckVerdict(enum.StrEnum):
    """Verdict values. Mirrors ``FactCheckVerdict`` in the frontend's ``lib/types.ts``."""

    TRUE = "true"
    FALSE = "false"
    MISLEADING = "misleading"
    UNVERIFIED = "unverified"


class FactCheck(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "fact_checks"

    room_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("debate_rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    verdict: Mapped[FactCheckVerdict] = mapped_column(
        SAEnum(
            FactCheckVerdict,
            name="fact_check_verdict",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    # Not in doc 04, but the UI renders it beside every verdict.
    explanation: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    sources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    room: Mapped["DebateRoom"] = relationship(back_populates="fact_checks")
    requester: Mapped["User"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<FactCheck id={self.id} verdict={self.verdict.value}>"
