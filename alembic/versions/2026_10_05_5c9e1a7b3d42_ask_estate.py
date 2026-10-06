"""ask estate

Revision ID: 5c9e1a7b3d42
Revises: 81126ee0b2b7
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5c9e1a7b3d42"
down_revision: str | None = "81126ee0b2b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ask_threads",
        sa.Column(
            "subject",
            sa.VARCHAR(length=16),
            server_default=sa.text("'asset'"),
            nullable=False,
        ),
    )
    op.add_column("ask_threads", sa.Column("scope", sa.JSON(), nullable=True))
    op.alter_column("ask_threads", "target_id", nullable=True)
    op.alter_column("ask_threads", "asset_key", nullable=True)
    op.create_index(
        "ix_ask_threads_estate",
        "ask_threads",
        ["project_id", "user_id", "subject", sa.text("last_at DESC")],
    )
    op.add_column(
        "ask_messages",
        sa.Column(
            "blocks", sa.JSON(), server_default=sa.text("'[]'::json"), nullable=False
        ),
    )
    op.add_column(
        "ask_messages",
        sa.Column(
            "follow_ups",
            sa.JSON(),
            server_default=sa.text("'[]'::json"),
            nullable=False,
        ),
    )
    op.add_column(
        "ask_messages", sa.Column("about", sa.VARCHAR(length=500), nullable=True)
    )
    op.add_column(
        "ask_messages",
        sa.Column(
            "intelligent",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("ask_messages", "intelligent")
    op.drop_column("ask_messages", "about")
    op.drop_column("ask_messages", "follow_ups")
    op.drop_column("ask_messages", "blocks")
    op.drop_index("ix_ask_threads_estate", table_name="ask_threads")
    op.execute("DELETE FROM ask_threads WHERE subject = 'estate'")
    op.alter_column("ask_threads", "asset_key", nullable=False)
    op.alter_column("ask_threads", "target_id", nullable=False)
    op.drop_column("ask_threads", "scope")
    op.drop_column("ask_threads", "subject")
