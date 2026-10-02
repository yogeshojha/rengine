"""ai pricing: cached tokens, the source of a cost, cache rates

Revision ID: 9a4c7e2d1b58
Revises: 7d3c9e5b1a46
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9a4c7e2d1b58"
down_revision: str | None = "7d3c9e5b1a46"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_calls",
        sa.Column(
            "cache_read_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "ai_calls",
        sa.Column(
            "cache_write_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "ai_calls", sa.Column("cost_source", sa.String(length=16), nullable=True)
    )
    op.add_column("ai_calls", sa.Column("input_per_mtok", sa.Float(), nullable=True))
    op.add_column("ai_calls", sa.Column("output_per_mtok", sa.Float(), nullable=True))
    op.add_column(
        "ai_connections", sa.Column("cache_read_per_mtok", sa.Float(), nullable=True)
    )
    op.add_column(
        "ai_connections", sa.Column("cache_write_per_mtok", sa.Float(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("ai_connections", "cache_write_per_mtok")
    op.drop_column("ai_connections", "cache_read_per_mtok")
    op.drop_column("ai_calls", "output_per_mtok")
    op.drop_column("ai_calls", "input_per_mtok")
    op.drop_column("ai_calls", "cost_source")
    op.drop_column("ai_calls", "cache_write_tokens")
    op.drop_column("ai_calls", "cache_read_tokens")
