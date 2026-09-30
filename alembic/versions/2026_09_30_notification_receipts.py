"""per-user notification read and dismiss state

Revision ID: f6c39a8b5d02
Revises: e5b28f7a4c91
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6c39a8b5d02"
down_revision: str | None = "e5b28f7a4c91"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "notification_receipts",
        sa.Column(
            "notification_id",
            sa.Integer(),
            sa.ForeignKey("notifications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("read_at", _TZ, nullable=True),
        sa.Column("dismissed_at", _TZ, nullable=True),
        sa.PrimaryKeyConstraint("notification_id", "user_id"),
    )
    op.create_index(
        "ix_notification_receipts_user_id", "notification_receipts", ["user_id"]
    )
    op.drop_index("ix_notifications_is_read", table_name="notifications")
    op.drop_column("notifications", "is_read")


def downgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.drop_index(
        "ix_notification_receipts_user_id", table_name="notification_receipts"
    )
    op.drop_table("notification_receipts")
