"""scans: pause/resume events and the canvas epoch

Revision ID: b7f41e0c9d26
Revises: e6b40f2a9c17
Create Date: 2026-09-13 09:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7f41e0c9d26"
down_revision: str | None = "e6b40f2a9c17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_VALUES = ("SCAN_PAUSED", "SCAN_RESUMED")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE activityevent ADD VALUE IF NOT EXISTS '{value}'")
    op.add_column(
        "scans",
        sa.Column("run_epoch", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("scans", sa.Column("paused_at", sa.DateTime(timezone=True)))
    op.add_column(
        "scans",
        sa.Column("paused_seconds", sa.Float(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("scans", "paused_seconds")
    op.drop_column("scans", "paused_at")
    op.drop_column("scans", "run_epoch")
