"""One built-in engine per project.

Revision ID: c9e4f2a71b58
Revises: b7d3e1f04a26
Create Date: 2026-09-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "c9e4f2a71b58"
down_revision: str | None = "b7d3e1f04a26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scan_engines",
        sa.Column(
            "builtin", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        "ux_scan_engines_builtin_project",
        "scan_engines",
        ["project_id"],
        unique=True,
        postgresql_where=sa.text("builtin"),
    )


def downgrade() -> None:
    op.drop_index("ux_scan_engines_builtin_project", table_name="scan_engines")
    op.drop_column("scan_engines", "builtin")
