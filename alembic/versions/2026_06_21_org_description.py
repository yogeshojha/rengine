"""add description column to organizations

Revision ID: e2a5c7d9f1b3
Revises: d1f4b6c8e0a2
Create Date: 2026-06-21 00:20:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2a5c7d9f1b3"
down_revision: str | None = "d1f4b6c8e0a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("description", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organizations", "description")
