"""User model.

Clerk owns authentication and the credential record; this table is the local mirror that
domain rows can foreign-key against. ``clerk_user_id`` is the join key — rows are created
or refreshed the first time a verified token is seen for that subject.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.topic import Topic


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    clerk_user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    # Remote URL (Clerk-hosted or uploaded); NULL means fall back to initials in the UI.
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_topics: Mapped[list["Topic"]] = relationship(
        back_populates="creator",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User id={self.id} username={self.username!r}>"
