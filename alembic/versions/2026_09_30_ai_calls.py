"""ai_calls: one row per provider call

Revision ID: b8e3d5f0a241
Revises: a7d2c4e9f130
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b8e3d5f0a241"
down_revision: str | None = "a7d2c4e9f130"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ai_calls",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("at", _TZ, nullable=False),
        sa.Column("task", sa.String(length=40), nullable=False),
        sa.Column("feature", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False),
        sa.Column("cached", sa.Boolean(), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=300), nullable=True),
        sa.Column("source_kind", sa.String(length=20), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_ai_calls_at", "ai_calls", ["at"])
    op.create_index("ix_ai_calls_feature_at", "ai_calls", ["feature", "at"])


def downgrade() -> None:
    op.drop_table("ai_calls")
