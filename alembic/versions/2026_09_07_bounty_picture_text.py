"""bounty_programs.profile_picture holds presigned URLs over 2 KB

Revision ID: e4b19d70c8a3
Revises: d17a83c6e2b4
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4b19d70c8a3"
down_revision: str | None = "d17a83c6e2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "bounty_programs",
        "profile_picture",
        existing_type=sa.String(length=1000),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.execute(
        "UPDATE bounty_programs SET profile_picture = NULL "
        "WHERE length(profile_picture) > 1000"
    )
    op.alter_column(
        "bounty_programs",
        "profile_picture",
        existing_type=sa.Text(),
        type_=sa.String(length=1000),
        existing_nullable=True,
    )
