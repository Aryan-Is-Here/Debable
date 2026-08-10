"""Initial schema: users, topics, debate rooms, messages, fact checks, ratings.

Implements ``docs/04-database-design.md`` with the agreed fixes from blueprint conflict
#4: timestamps on every table and ``fact_checks.sources`` as JSONB.

Revision ID: 0001
Revises:
Create Date: 2026-08-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# create_type=False: the types are created explicitly in upgrade() so that downgrade()
# has something matching to drop.
topic_status = postgresql.ENUM("open", "active", "archived", name="topic_status", create_type=False)
fact_check_verdict = postgresql.ENUM(
    "true", "false", "misleading", "unverified", name="fact_check_verdict", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    topic_status.create(bind, checkfirst=True)
    fact_check_verdict.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_clerk_user_id"), "users", ["clerk_user_id"], unique=True)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=True)

    op.create_table(
        "topics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", topic_status, server_default="open", nullable=False),
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
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_topics_creator_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_topics")),
    )
    op.create_index(op.f("ix_topics_creator_id"), "topics", ["creator_id"], unique=False)
    op.create_index(op.f("ix_topics_status"), "topics", ["status"], unique=False)
    op.create_index(op.f("ix_topics_title"), "topics", ["title"], unique=False)

    op.create_table(
        "debate_rooms",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("topic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user1_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user2_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.CheckConstraint("user1_id <> user2_id", name=op.f("ck_debate_rooms_distinct_users")),
        sa.ForeignKeyConstraint(
            ["topic_id"],
            ["topics.id"],
            name=op.f("fk_debate_rooms_topic_id_topics"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user1_id"],
            ["users.id"],
            name=op.f("fk_debate_rooms_user1_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user2_id"],
            ["users.id"],
            name=op.f("fk_debate_rooms_user2_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_debate_rooms")),
    )
    op.create_index(op.f("ix_debate_rooms_topic_id"), "debate_rooms", ["topic_id"], unique=False)
    op.create_index(op.f("ix_debate_rooms_user1_id"), "debate_rooms", ["user1_id"], unique=False)
    op.create_index(op.f("ix_debate_rooms_user2_id"), "debate_rooms", ["user2_id"], unique=False)

    op.create_table(
        "messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
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
            ["room_id"],
            ["debate_rooms.id"],
            name=op.f("fk_messages_room_id_debate_rooms"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.id"],
            name=op.f("fk_messages_sender_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_messages")),
    )
    op.create_index(
        "ix_messages_room_id_created_at", "messages", ["room_id", "created_at"], unique=False
    )
    op.create_index(op.f("ix_messages_sender_id"), "messages", ["sender_id"], unique=False)

    op.create_table(
        "fact_checks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requester_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("verdict", fact_check_verdict, nullable=False),
        sa.Column("explanation", sa.Text(), server_default="", nullable=False),
        sa.Column(
            "sources",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
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
            ["requester_id"],
            ["users.id"],
            name=op.f("fk_fact_checks_requester_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["debate_rooms.id"],
            name=op.f("fk_fact_checks_room_id_debate_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fact_checks")),
    )
    op.create_index(
        op.f("ix_fact_checks_requester_id"), "fact_checks", ["requester_id"], unique=False
    )
    op.create_index(op.f("ix_fact_checks_room_id"), "fact_checks", ["room_id"], unique=False)

    op.create_table(
        "ratings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("room_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewed_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
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
            "reviewer_id <> reviewed_user_id", name=op.f("ck_ratings_no_self_review")
        ),
        sa.CheckConstraint("score BETWEEN 1 AND 5", name=op.f("ck_ratings_score_range")),
        sa.ForeignKeyConstraint(
            ["reviewed_user_id"],
            ["users.id"],
            name=op.f("fk_ratings_reviewed_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["reviewer_id"],
            ["users.id"],
            name=op.f("fk_ratings_reviewer_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["room_id"],
            ["debate_rooms.id"],
            name=op.f("fk_ratings_room_id_debate_rooms"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ratings")),
        sa.UniqueConstraint("room_id", "reviewer_id", name="uq_ratings_room_reviewer"),
    )
    op.create_index(
        op.f("ix_ratings_reviewed_user_id"), "ratings", ["reviewed_user_id"], unique=False
    )
    op.create_index(op.f("ix_ratings_reviewer_id"), "ratings", ["reviewer_id"], unique=False)
    op.create_index(op.f("ix_ratings_room_id"), "ratings", ["room_id"], unique=False)


def downgrade() -> None:
    op.drop_table("ratings")
    op.drop_table("fact_checks")
    op.drop_table("messages")
    op.drop_table("debate_rooms")
    op.drop_table("topics")
    op.drop_table("users")

    bind = op.get_bind()
    fact_check_verdict.drop(bind, checkfirst=True)
    topic_status.drop(bind, checkfirst=True)
