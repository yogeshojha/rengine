"""add subdomains

Revision ID: f3b7d1a9c2e4
Revises: e2a5c7d9f1b3
Create Date: 2026-06-21 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b7d1a9c2e4"
down_revision: str | None = "e2a5c7d9f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "subdomains",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("resolved_ips", sa.JSON(), nullable=False),
        sa.Column("cname", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_wildcard", sa.Boolean(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "name", name="uq_subdomain_scan_name"),
    )
    op.create_index(op.f("ix_subdomains_id"), "subdomains", ["id"], unique=False)
    op.create_index(
        op.f("ix_subdomains_scan_id"), "subdomains", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_subdomains_target_id"), "subdomains", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_subdomains_project_id"), "subdomains", ["project_id"], unique=False
    )
    op.create_index(op.f("ix_subdomains_name"), "subdomains", ["name"], unique=False)
    op.create_index(
        op.f("ix_subdomains_is_active"), "subdomains", ["is_active"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subdomains_is_active"), table_name="subdomains")
    op.drop_index(op.f("ix_subdomains_name"), table_name="subdomains")
    op.drop_index(op.f("ix_subdomains_project_id"), table_name="subdomains")
    op.drop_index(op.f("ix_subdomains_target_id"), table_name="subdomains")
    op.drop_index(op.f("ix_subdomains_scan_id"), table_name="subdomains")
    op.drop_index(op.f("ix_subdomains_id"), table_name="subdomains")
    op.drop_table("subdomains")
