"""activity logs: scan linkage + denormalized target, stage/cancel events

Revision ID: f4a6c8e0b2d1
Revises: e2b5d8c14f37
Create Date: 2026-09-02 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4a6c8e0b2d1"
down_revision: str | None = "e2b5d8c14f37"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_VALUES = ("SCAN_CANCELLED", "SCAN_STAGE_COMPLETED", "SCAN_STAGE_FAILED")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE activityevent ADD VALUE IF NOT EXISTS '{value}'")
    # no FK on scan_id and a stored target name: the trail must outlive scan/target deletion
    op.add_column("activity_logs", sa.Column("scan_id", sa.Uuid(), nullable=True))
    op.create_index("ix_activity_logs_scan_id", "activity_logs", ["scan_id"])
    op.add_column(
        "activity_logs", sa.Column("target_value", sa.String(length=500), nullable=True)
    )
    op.execute(
        "UPDATE activity_logs SET target_value = targets.target_value "
        "FROM targets WHERE activity_logs.target_id = targets.id"
    )


def downgrade() -> None:
    op.drop_column("activity_logs", "target_value")
    op.drop_index("ix_activity_logs_scan_id", table_name="activity_logs")
    op.drop_column("activity_logs", "scan_id")
