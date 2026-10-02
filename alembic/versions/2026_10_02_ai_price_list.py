"""ai price list: model prices as a dataset, a price set on a provider

Revision ID: c5e1f9a3b7d2
Revises: 9a4c7e2d1b58
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c5e1f9a3b7d2"
down_revision: str | None = "9a4c7e2d1b58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_prices",
        sa.Column("model_id", sa.String(length=120), primary_key=True),
        sa.Column("input_per_mtok", sa.Float(), nullable=False),
        sa.Column("output_per_mtok", sa.Float(), nullable=False),
        sa.Column("cache_read_per_mtok", sa.Float(), nullable=True),
        sa.Column("cache_write_per_mtok", sa.Float(), nullable=True),
    )
    op.add_column(
        "ai_connections",
        sa.Column(
            "custom_price", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("ai_connections", "custom_price")
    op.drop_table("ai_prices")
