"""Add topics.category.

Resolves blueprint conflict #6: the frontend has filtered on a category since Phase 1, but
it existed only as a UI-only field with no column behind it. Stored as a plain indexed
varchar; allowed values are enforced by the API schema, not the database (see
``app/core/categories.py``).

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Added with a server default so the column can be NOT NULL even if rows already exist,
    # then dropped so the application must always supply a value.
    op.add_column(
        "topics",
        sa.Column("category", sa.String(length=40), nullable=False, server_default="Society"),
    )
    op.alter_column("topics", "category", server_default=None)
    op.create_index(op.f("ix_topics_category"), "topics", ["category"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_topics_category"), table_name="topics")
    op.drop_column("topics", "category")
