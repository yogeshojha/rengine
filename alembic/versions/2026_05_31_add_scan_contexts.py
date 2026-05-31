"""add scan contexts

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-31 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_contexts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.Column("auth_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("auth", sa.JSON(), nullable=False),
        sa.Column("extra_headers", sa.JSON(), nullable=False),
        sa.Column("global_rate_limit_override", sa.Integer(), nullable=True),
        sa.Column("per_tool_rate_overrides", sa.JSON(), nullable=False),
        sa.Column("thread_multiplier", sa.Float(), nullable=False),
        sa.Column("timeout_multiplier", sa.Float(), nullable=False),
        sa.Column("excluded_subdomains", sa.JSON(), nullable=False),
        sa.Column("excluded_paths", sa.JSON(), nullable=False),
        sa.Column("excluded_ips", sa.JSON(), nullable=False),
        sa.Column("included_subdomains", sa.JSON(), nullable=False),
        sa.Column("follow_redirects_override", sa.Boolean(), nullable=True),
        sa.Column("http_protocol", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("compare_baseline_scan_id", sa.Uuid(), nullable=True),
        sa.Column("scan_only_new_assets", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_scan_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_contexts_id"), "scan_contexts", ["id"], unique=False)
    op.create_index(
        op.f("ix_scan_contexts_project_id"),
        "scan_contexts",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scan_contexts_project_id"), table_name="scan_contexts")
    op.drop_index(op.f("ix_scan_contexts_id"), table_name="scan_contexts")
    op.drop_table("scan_contexts")
