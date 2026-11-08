"""drop the unused api key usage columns

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
Create Date: 2026-11-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e3c4d5f6a7b8"
down_revision: str | None = "d2b3c4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("api_keys", "usage_counter")
    op.drop_column("api_keys", "last_used_at")


def downgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column(
            "usage_counter", sa.INTEGER(), nullable=False, server_default=sa.text("0")
        ),
    )
    op.alter_column("api_keys", "usage_counter", server_default=None)
    op.add_column(
        "api_keys",
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
    )
