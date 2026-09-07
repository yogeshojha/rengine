"""instance_settings.bounty_settings: notification preferences for program changes

Revision ID: c8e35a71d904
Revises: a2d64f8b31c7
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c8e35a71d904"
down_revision: str | None = "a2d64f8b31c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column(
            "bounty_settings",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "bounty_settings")
