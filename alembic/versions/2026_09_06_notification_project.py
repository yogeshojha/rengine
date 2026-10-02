"""notifications: scope a notification to its project

Revision ID: c4b8e1f70a92
Revises: a91d47c30fb2
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4b8e1f70a92"
down_revision: str | None = "a91d47c30fb2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("project_id", sa.Uuid(), nullable=True))
    op.create_index("ix_notifications_project_id", "notifications", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_notifications_project_id", table_name="notifications")
    op.drop_column("notifications", "project_id")
