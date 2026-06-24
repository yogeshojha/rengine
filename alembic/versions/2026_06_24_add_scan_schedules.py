"""add scan_schedules (continuous monitoring) + scans.schedule_id

Revision ID: a1d3f5b7c9e2
Revises: c9f2a4e6b1d8
Create Date: 2026-06-24 12:00:00.000000+00:00

DB-backed scan schedules (one-off / interval / daily / cron) polled by the beat tick,
plus the schedule_id back-link on spawned scans.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "a1d3f5b7c9e2"
down_revision: str | None = "c9f2a4e6b1d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_schedules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column("target_ids", sa.JSON(), nullable=False),
        sa.Column("engine_id", sa.Uuid(), nullable=False),
        sa.Column(
            "engine_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False
        ),
        sa.Column("context_id", sa.Uuid(), nullable=True),
        sa.Column(
            "context_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True
        ),
        sa.Column("schedule_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interval_every", sa.Integer(), nullable=True),
        sa.Column(
            "interval_unit", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True
        ),
        sa.Column(
            "daily_at_time", sqlmodel.sql.sqltypes.AutoString(length=5), nullable=True
        ),
        sa.Column(
            "cron_expression",
            sqlmodel.sql.sqltypes.AutoString(length=120),
            nullable=True,
        ),
        sa.Column(
            "timezone", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_error", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("total_run_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_schedules_id"), "scan_schedules", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_scan_schedules_project_id"),
        "scan_schedules",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_schedules_engine_id"),
        "scan_schedules",
        ["engine_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_schedules_schedule_type"),
        "scan_schedules",
        ["schedule_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_schedules_status"), "scan_schedules", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_scan_schedules_next_run_at"),
        "scan_schedules",
        ["next_run_at"],
        unique=False,
    )

    op.add_column("scans", sa.Column("schedule_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_scans_schedule_id"), "scans", ["schedule_id"], unique=False
    )
    op.create_foreign_key(
        "fk_scans_schedule_id",
        "scans",
        "scan_schedules",
        ["schedule_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_scans_schedule_id", "scans", type_="foreignkey")
    op.drop_index(op.f("ix_scans_schedule_id"), table_name="scans")
    op.drop_column("scans", "schedule_id")

    op.drop_index(op.f("ix_scan_schedules_next_run_at"), table_name="scan_schedules")
    op.drop_index(op.f("ix_scan_schedules_status"), table_name="scan_schedules")
    op.drop_index(op.f("ix_scan_schedules_schedule_type"), table_name="scan_schedules")
    op.drop_index(op.f("ix_scan_schedules_engine_id"), table_name="scan_schedules")
    op.drop_index(op.f("ix_scan_schedules_project_id"), table_name="scan_schedules")
    op.drop_index(op.f("ix_scan_schedules_id"), table_name="scan_schedules")
    op.drop_table("scan_schedules")
