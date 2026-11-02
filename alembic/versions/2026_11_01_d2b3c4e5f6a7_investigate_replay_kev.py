"""instance toggle for the known-exploited replay rule

Revision ID: d2b3c4e5f6a7
Revises: c1a2b3d4e5f6
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2b3c4e5f6a7"
down_revision: str | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column(
            "investigate_replay_kev",
            sa.BOOLEAN(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("instance_settings", "investigate_replay_kev", server_default=None)


def downgrade() -> None:
    op.drop_column("instance_settings", "investigate_replay_kev")
