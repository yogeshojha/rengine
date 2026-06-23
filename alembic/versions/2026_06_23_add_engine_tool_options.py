"""add scan_engines.tool_options (per-tool custom CLI args)

Revision ID: c9f2a4e6b1d8
Revises: b8e1f4a2c6d9
Create Date: 2026-06-23 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c9f2a4e6b1d8"
down_revision: str | None = "b8e1f4a2c6d9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scan_engines",
        sa.Column("tool_options", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("scan_engines", "tool_options")
