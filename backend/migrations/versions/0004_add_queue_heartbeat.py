"""Add a liveness heartbeat to the matchmaking queue.

Closing a browser tab never withdrew the user from the queue, leaving rows that other
people were then matched against — an opponent who was not there. Unload handlers cannot
fix this reliably, so presence is proven by continuing to poll instead.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "match_queue",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        op.f("ix_match_queue_last_seen_at"), "match_queue", ["last_seen_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_match_queue_last_seen_at"), table_name="match_queue")
    op.drop_column("match_queue", "last_seen_at")
