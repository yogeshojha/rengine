"""tripwires, their checks and the live marks

Revision ID: e5b28f7a4c91
Revises: d4a17e9b3c58
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e5b28f7a4c91"
down_revision: str | None = "d4a17e9b3c58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.execute("ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'TRIPWIRE'")

    op.create_table(
        "tripwires",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("query", sa.String(length=2000), nullable=False),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("fire_on", sa.String(length=16), nullable=False),
        sa.Column("scope_kind", sa.String(length=16), nullable=False),
        sa.Column("scope_ids", sa.JSON(), nullable=False),
        sa.Column("actions", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("fired_count", sa.Integer(), nullable=False),
        sa.Column("last_fired_at", _TZ, nullable=True),
        sa.Column("last_checked_at", _TZ, nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
    )
    op.create_index("ix_tripwires_project_id", "tripwires", ["project_id"])
    op.create_index(
        "ix_tripwires_project_enabled", "tripwires", ["project_id", "enabled"]
    )

    op.create_table(
        "tripwire_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tripwire_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("matched", sa.Integer(), nullable=False),
        sa.Column("fired", sa.Integer(), nullable=False),
        sa.Column("rows", sa.JSON(), nullable=False),
        sa.Column("outcomes", sa.JSON(), nullable=False),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("checked_at", _TZ, nullable=False),
        sa.Column("fired_at", _TZ, nullable=True),
        sa.ForeignKeyConstraint(["tripwire_id"], ["tripwires.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tripwire_id", "scan_id", name="uq_tripwire_run"),
    )
    for column in ("tripwire_id", "project_id", "target_id", "scan_id", "status"):
        op.create_index(f"ix_tripwire_runs_{column}", "tripwire_runs", [column])
    op.create_index(
        "ix_tripwire_runs_tripwire_checked",
        "tripwire_runs",
        ["tripwire_id", "checked_at"],
    )
    op.create_index(
        "ix_tripwire_runs_project_fired", "tripwire_runs", ["project_id", "fired_at"]
    )

    op.create_table(
        "tripwire_marks",
        sa.Column("tripwire_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=600), nullable=False),
        sa.Column("marked_at", _TZ, nullable=False),
        sa.ForeignKeyConstraint(["tripwire_id"], ["tripwires.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("tripwire_id", "scan_id", "key"),
    )
    op.create_index("ix_tripwire_marks_scan_id", "tripwire_marks", ["scan_id"])


def downgrade() -> None:
    op.drop_table("tripwire_marks")
    op.drop_table("tripwire_runs")
    op.drop_table("tripwires")
