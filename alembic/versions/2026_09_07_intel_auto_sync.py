"""instance settings: nightly exploitation-feed download is opt-out

Revision ID: b62f04a1d7e9
Revises: a41d7e93c05b
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b62f04a1d7e9"
down_revision: str | None = "a41d7e93c05b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column(
            "threat_intel_auto_sync",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "threat_intel_auto_sync")
