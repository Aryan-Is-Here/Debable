"""Add the reports table.

Resolves blueprint conflict #1, the last open gap: the PRD lists a Reports feature and
``docs/05-api-specification.md`` has ``POST /report``, but ``docs/04-database-design.md``
never had a table for it. This is the final migration in the project — everything built
since Phase 2 fitted the original schema.

``category`` is a plain indexed varchar; allowed values are enforced by the API schema
rather than the database, the same decision as ``topics.category`` (see
``app/core/reports.py``).

Deliberately no status, assignee or resolution column. The MVP has no moderator, so a report
is a record rather than a workflow, and columns implying a process that does not exist would
be a lie told in schema.

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reports",
        sa.Column("room_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("reported_user_id", sa.UUID(), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint(
            "reporter_id <> reported_user_id", name=op.f("ck_reports_no_self_report")
        ),
        sa.ForeignKeyConstraint(
            ["reported_user_id"],
            ["users.id"],
            name=op.f("fk_reports_reported_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name=op.f("fk_reports_reporter_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["debate_rooms.id"],
            name=op.f("fk_reports_room_id_debate_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
        sa.UniqueConstraint("room_id", "reporter_id", name="uq_reports_room_reporter"),
    )
    op.create_index(op.f("ix_reports_category"), "reports", ["category"], unique=False)
    op.create_index(
        op.f("ix_reports_reported_user_id"), "reports", ["reported_user_id"], unique=False
    )
    op.create_index(op.f("ix_reports_reporter_id"), "reports", ["reporter_id"], unique=False)
    op.create_index(op.f("ix_reports_room_id"), "reports", ["room_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_room_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_reporter_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_reported_user_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_category"), table_name="reports")
    op.drop_table("reports")
