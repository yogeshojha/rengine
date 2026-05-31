"""add scans

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-31 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scans",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("engine_id", sa.Uuid(), nullable=False),
        sa.Column(
            "engine_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False
        ),
        sa.Column("context_id", sa.Uuid(), nullable=True),
        sa.Column(
            "context_name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=True
        ),
        sa.Column("execution_config", sa.JSON(), nullable=False),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("subdomains_found", sa.Integer(), nullable=False),
        sa.Column("ips_found", sa.Integer(), nullable=False),
        sa.Column("open_ports_found", sa.Integer(), nullable=False),
        sa.Column("vulnerabilities_found", sa.Integer(), nullable=False),
        sa.Column("endpoints_found", sa.Integer(), nullable=False),
        sa.Column(
            "error", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["engine_id"],
            ["scan_engines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scans_id"), "scans", ["id"], unique=False)
    op.create_index(op.f("ix_scans_project_id"), "scans", ["project_id"], unique=False)
    op.create_index(op.f("ix_scans_target_id"), "scans", ["target_id"], unique=False)
    op.create_index(op.f("ix_scans_status"), "scans", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scans_status"), table_name="scans")
    op.drop_index(op.f("ix_scans_target_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_project_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_id"), table_name="scans")
    op.drop_table("scans")
