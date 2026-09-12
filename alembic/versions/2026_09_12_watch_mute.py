"""watch host mute keeps the prior state

Revision ID: 9e4b7c31a2d6
Revises: 7c2e9a41b5d8
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9e4b7c31a2d6"
down_revision: str | None = "7c2e9a41b5d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "watch_hosts", sa.Column("muted_from", sa.String(length=16), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("watch_hosts", "muted_from")
