"""api_keys test status, notification_channels delivery status, proxies without mode

Revision ID: 5d2e9a8c1b47
Revises: a1f4c7d20e93
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5d2e9a8c1b47"
down_revision: str | None = "a1f4c7d20e93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "api_keys", sa.Column("last_test_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("api_keys", sa.Column("last_test_ok", sa.Boolean(), nullable=True))
    op.add_column(
        "api_keys", sa.Column("last_test_message", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "notification_channels",
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_channels", sa.Column("last_sent_ok", sa.Boolean(), nullable=True)
    )
    op.add_column(
        "notification_channels",
        sa.Column("last_sent_message", sa.String(length=500), nullable=True),
    )
    op.drop_column("proxies", "mode")


def downgrade() -> None:
    op.add_column(
        "proxies",
        sa.Column("mode", sa.String(), nullable=False, server_default="single"),
    )
    op.drop_column("notification_channels", "last_sent_message")
    op.drop_column("notification_channels", "last_sent_ok")
    op.drop_column("notification_channels", "last_sent_at")
    op.drop_column("api_keys", "last_test_message")
    op.drop_column("api_keys", "last_test_ok")
    op.drop_column("api_keys", "last_test_at")
