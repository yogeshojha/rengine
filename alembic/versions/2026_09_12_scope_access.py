"""record why a program's scope could not be read

Revision ID: b7c2d81e4a96
Revises: a4f1c07b9d32
Create Date: 2026-09-12 22:10:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c2d81e4a96"
down_revision: str | None = "a4f1c07b9d32"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bounty_programs",
        sa.Column("scope_access", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("bounty_programs", "scope_access")
