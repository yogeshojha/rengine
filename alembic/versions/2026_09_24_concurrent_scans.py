"""concurrent scan limit

Revision ID: 7a2e9c4b1f60
Revises: 8b3f61c0d2a7
Create Date: 2026-09-24 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7a2e9c4b1f60"
down_revision: str | None = "8b3f61c0d2a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column(
            "concurrent_scans", sa.Integer(), nullable=False, server_default="0"
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "concurrent_scans")
