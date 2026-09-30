"""ask threads and messages on a finding or a web asset

Revision ID: a7d2c4e9f130
Revises: f6c39a8b5d02
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a7d2c4e9f130"
down_revision: str | None = "f6c39a8b5d02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ask_threads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("asset_key", sa.String(length=500), nullable=False),
        sa.Column("title", sa.String(length=80), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("last_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    for column in ("project_id", "target_id", "user_id"):
        op.create_index(f"ix_ask_threads_{column}", "ask_threads", [column])
    op.create_index(
        "ix_ask_threads_asset",
        "ask_threads",
        ["target_id", "dimension", "asset_key", "user_id"],
    )

    op.create_table(
        "ask_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("thread_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("suggestion", sa.JSON(), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["ask_threads.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_ask_messages_thread_id", "ask_messages", ["thread_id"])
    op.create_index(
        "ix_ask_messages_thread_created", "ask_messages", ["thread_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("ask_messages")
    op.drop_table("ask_threads")
