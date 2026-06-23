"""add scan orchestration tables (scan_activities, scan_commands) + scan.celery_task_ids

Revision ID: b8e1f4a2c6d9
Revises: d5f7b9c1e3a4
Create Date: 2026-06-22 23:00:00.000000+00:00

Per-stage activity timeline + per-command registration & log capture for the
scan orchestrator, plus the celery task-id abort handle on scans.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "b8e1f4a2c6d9"
down_revision: str | None = "d5f7b9c1e3a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column(
            "celery_task_ids", sa.JSON(), nullable=False, server_default="[]"
        ),
    )

    op.create_table(
        "scan_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column(
            "title", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False
        ),
        sa.Column(
            "status", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column(
            "celery_task_id",
            sqlmodel.sql.sqltypes.AutoString(length=100),
            nullable=True,
        ),
        sa.Column(
            "error", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("traceback", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_activities_id"), "scan_activities", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_scan_activities_scan_id"),
        "scan_activities",
        ["scan_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_activities_project_id"),
        "scan_activities",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_activities_name"), "scan_activities", ["name"], unique=False
    )
    op.create_index(
        op.f("ix_scan_activities_status"),
        "scan_activities",
        ["status"],
        unique=False,
    )

    op.create_table(
        "scan_commands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("tool", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("return_code", sa.Integer(), nullable=True),
        sa.Column("output", sa.Text(), nullable=True),
        sa.Column(
            "error", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["activity_id"], ["scan_activities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scan_commands_id"), "scan_commands", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_scan_commands_scan_id"), "scan_commands", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_scan_commands_activity_id"),
        "scan_commands",
        ["activity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_commands_project_id"),
        "scan_commands",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scan_commands_tool"), "scan_commands", ["tool"], unique=False
    )
    op.create_index(
        op.f("ix_scan_commands_status"), "scan_commands", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scan_commands_status"), table_name="scan_commands")
    op.drop_index(op.f("ix_scan_commands_tool"), table_name="scan_commands")
    op.drop_index(op.f("ix_scan_commands_project_id"), table_name="scan_commands")
    op.drop_index(op.f("ix_scan_commands_activity_id"), table_name="scan_commands")
    op.drop_index(op.f("ix_scan_commands_scan_id"), table_name="scan_commands")
    op.drop_index(op.f("ix_scan_commands_id"), table_name="scan_commands")
    op.drop_table("scan_commands")

    op.drop_index(op.f("ix_scan_activities_status"), table_name="scan_activities")
    op.drop_index(op.f("ix_scan_activities_name"), table_name="scan_activities")
    op.drop_index(op.f("ix_scan_activities_project_id"), table_name="scan_activities")
    op.drop_index(op.f("ix_scan_activities_scan_id"), table_name="scan_activities")
    op.drop_index(op.f("ix_scan_activities_id"), table_name="scan_activities")
    op.drop_table("scan_activities")

    op.drop_column("scans", "celery_task_ids")
