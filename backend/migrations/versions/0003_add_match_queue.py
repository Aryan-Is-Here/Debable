"""Add the matchmaking queue.

Resolves blueprint conflict #2. One row per waiting user; rows are deleted as soon as a
pair is formed. See ``app/models/match_queue.py`` for why this lives in Postgres rather
than process memory.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "match_queue",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_match_queue_topic_id_topics"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_match_queue_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_match_queue")),
    )
    # A user can only be waiting for one debate at a time.
    op.create_index(op.f("ix_match_queue_user_id"), "match_queue", ["user_id"], unique=True)
    op.create_index(
        "ix_match_queue_topic_id_created_at",
        "match_queue",
        ["topic_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("match_queue")
