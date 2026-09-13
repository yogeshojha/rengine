"""exports: a saved recipe and the file its run produced

Revision ID: a18f3c7d5e92
Revises: d51c7a2e9f04
Create Date: 2026-09-13 14:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a18f3c7d5e92"
down_revision: str | None = "d51c7a2e9f04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("scan_id", sa.Uuid()),
        sa.Column("target_id", sa.Uuid()),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("query", sa.String(length=2000), nullable=False),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("export_format", sa.String(length=16), nullable=False),
        sa.Column("include_evidence", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(length=100), nullable=False),
        sa.Column("error", sa.String(length=2000)),
        sa.Column("task_id", sa.String(length=100)),
        sa.Column("filename", sa.String(length=255)),
        sa.Column("bytes_written", sa.BigInteger(), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("capped", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_seconds", sa.Float()),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_exports_project_id", "exports", ["project_id"])
    op.create_index("ix_exports_scan_id", "exports", ["scan_id"])
    op.create_index("ix_exports_target_id", "exports", ["target_id"])
    op.create_index("ix_exports_created_at", "exports", ["created_at"])
    op.create_index("ix_exports_status", "exports", ["status"])
    op.create_index("ix_exports_dimension", "exports", ["dimension"])
    op.create_index("ix_exports_expires_at", "exports", ["expires_at"])


def downgrade() -> None:
    for name in (
        "ix_exports_expires_at",
        "ix_exports_dimension",
        "ix_exports_status",
        "ix_exports_created_at",
        "ix_exports_target_id",
        "ix_exports_scan_id",
        "ix_exports_project_id",
    ):
        op.drop_index(name, table_name="exports")
    op.drop_table("exports")
