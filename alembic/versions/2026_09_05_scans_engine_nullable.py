"""scans.engine_id nullable: a launch may run an ad hoc plan with no saved engine

Revision ID: c9d2a7f13e58
Revises: b8e3f52c1a70
Create Date: 2026-09-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9d2a7f13e58"
down_revision: str | None = "b8e3f52c1a70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("scans", "engine_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM scans WHERE engine_id IS NULL")
    op.alter_column("scans", "engine_id", existing_type=sa.Uuid(), nullable=False)
