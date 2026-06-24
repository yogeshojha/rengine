"""scans.schedule_type + composite tick index

Revision ID: b2e4c6a8d0f1
Revises: a1d3f5b7c9e2
Create Date: 2026-06-24 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2e4c6a8d0f1"
down_revision: str | None = "a1d3f5b7c9e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans", sa.Column("schedule_type", sa.String(length=20), nullable=True)
    )
    op.create_index(
        "ix_scan_schedules_status_next_run",
        "scan_schedules",
        ["status", "next_run_at"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_scan_schedules_next_run_at"), table_name="scan_schedules"
    )


def downgrade() -> None:
    op.create_index(
        op.f("ix_scan_schedules_next_run_at"),
        "scan_schedules",
        ["next_run_at"],
        unique=False,
    )
    op.drop_index("ix_scan_schedules_status_next_run", table_name="scan_schedules")
    op.drop_column("scans", "schedule_type")
