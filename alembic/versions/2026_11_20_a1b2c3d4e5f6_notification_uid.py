"""notification public id

Revision ID: a1b2c3d4e5f6
Revises: f0a1b2c3d4e5
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "f0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "uid",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.alter_column("notifications", "uid", server_default=None)
    op.create_index("ix_notifications_uid", "notifications", ["uid"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notifications_uid", table_name="notifications")
    op.drop_column("notifications", "uid")
