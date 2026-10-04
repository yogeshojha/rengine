"""drop ai custom price

Revision ID: cb7bd70d3f2e
Revises: 3f8b2d6c1a94
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "cb7bd70d3f2e"
down_revision: str | None = "3f8b2d6c1a94"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("ai_connections", "custom_price")


def downgrade() -> None:
    op.add_column(
        "ai_connections",
        sa.Column(
            "custom_price",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
