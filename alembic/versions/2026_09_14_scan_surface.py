"""scan surface: what the vulnerability scanner was handed, per tier and batch

Revision ID: a4c2e7d91f53
Revises: f1a9c62d7b34
Create Date: 2026-09-14 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4c2e7d91f53"
down_revision: str | None = "f1a9c62d7b34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_surface_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("class", sa.String(length=16), nullable=False),
        sa.Column("value", sa.String(length=2000), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("scheme", sa.String(length=8), nullable=True),
        sa.Column("http_asset_id", sa.Uuid(), nullable=True),
        sa.Column("endpoint_id", sa.Uuid(), nullable=True),
        sa.Column("port_id", sa.Uuid(), nullable=True),
        sa.Column("subdomain_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_id", sa.Uuid(), nullable=True),
        sa.Column("representative_id", sa.Uuid(), nullable=True),
        sa.Column("cluster_signals", sa.JSON(), nullable=False),
        sa.Column("members", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("drop_reason", sa.String(length=32), nullable=True),
        sa.Column("rank", sa.Float(), nullable=False, server_default="0"),
        sa.Column("batch", sa.Integer(), nullable=True),
        sa.Column("guarded", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column("unmapped_tech", sa.JSON(), nullable=False),
        sa.Column("tiers_planned", sa.JSON(), nullable=False),
        sa.Column("tiers_done", sa.JSON(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
    )
    op.create_index("ix_scan_surface_items_scan_id", "scan_surface_items", ["scan_id"])
    op.create_index(
        "ix_scan_surface_items_target_id", "scan_surface_items", ["target_id"]
    )
    op.create_index(
        "ix_scan_surface_items_project_id", "scan_surface_items", ["project_id"]
    )
    op.create_index(
        "ix_scan_surface_items_cluster_id", "scan_surface_items", ["cluster_id"]
    )
    op.create_index(
        "ix_scan_surface_items_representative_id",
        "scan_surface_items",
        ["representative_id"],
    )
    op.create_index(
        "ix_scan_surface_scan_class", "scan_surface_items", ["scan_id", "class"]
    )
    op.create_index(
        "ix_scan_surface_scan_asset", "scan_surface_items", ["scan_id", "http_asset_id"]
    )
    op.create_index(
        "ix_scan_surface_target_value", "scan_surface_items", ["target_id", "value"]
    )

    op.add_column(
        "vulnerability_coverage",
        sa.Column("tier", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "vulnerability_coverage", sa.Column("batch", sa.Integer(), nullable=True)
    )
    op.add_column(
        "vulnerability_coverage",
        sa.Column("hosts_covered", sa.Integer(), nullable=False, server_default="0"),
    )

    op.add_column(
        "vulnerabilities", sa.Column("replayed_from_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        "ix_vulnerabilities_replayed_from_id",
        "vulnerabilities",
        ["replayed_from_id"],
        postgresql_where=sa.text("replayed_from_id IS NOT NULL"),
    )

    op.add_column("vuln_templates", sa.Column("paths", sa.JSON(), nullable=True))
    op.add_column("vuln_templates", sa.Column("simple", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("vuln_templates", "simple")
    op.drop_column("vuln_templates", "paths")
    op.drop_index("ix_vulnerabilities_replayed_from_id", table_name="vulnerabilities")
    op.drop_column("vulnerabilities", "replayed_from_id")
    op.drop_column("vulnerability_coverage", "hosts_covered")
    op.drop_column("vulnerability_coverage", "batch")
    op.drop_column("vulnerability_coverage", "tier")
    for name in (
        "ix_scan_surface_target_value",
        "ix_scan_surface_scan_asset",
        "ix_scan_surface_scan_class",
        "ix_scan_surface_items_representative_id",
        "ix_scan_surface_items_cluster_id",
        "ix_scan_surface_items_project_id",
        "ix_scan_surface_items_target_id",
        "ix_scan_surface_items_scan_id",
    ):
        op.drop_index(name, table_name="scan_surface_items")
    op.drop_table("scan_surface_items")
