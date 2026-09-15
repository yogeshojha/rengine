"""domain posture: sender, mail and zone checks per registrable domain

Revision ID: e4a1c7b92d63
Revises: d2f8a6c31e97
Create Date: 2026-09-15 04:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e4a1c7b92d63"
down_revision: str | None = "d2f8a6c31e97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_subdomains_posture_gin"


def upgrade() -> None:
    op.create_table(
        "domain_posture",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("zone", sa.String(length=253), nullable=False),
        sa.Column("hosts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("spf", sa.Text(), nullable=True),
        sa.Column("spf_all", sa.String(length=16), nullable=True),
        sa.Column("spf_lookups", sa.Integer(), nullable=True),
        sa.Column("dmarc", sa.Text(), nullable=True),
        sa.Column("dmarc_policy", sa.String(length=16), nullable=True),
        sa.Column("dmarc_subdomain_policy", sa.String(length=16), nullable=True),
        sa.Column("dmarc_pct", sa.Integer(), nullable=True),
        sa.Column("dmarc_rua", sa.Boolean(), nullable=True),
        sa.Column("dkim_selectors", sa.JSON(), nullable=False),
        sa.Column("dkim_key_bits", sa.Integer(), nullable=True),
        sa.Column("mx", sa.JSON(), nullable=False),
        sa.Column("null_mx", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mta_sts", sa.String(length=500), nullable=True),
        sa.Column("mta_sts_mode", sa.String(length=16), nullable=True),
        sa.Column("tls_rpt", sa.String(length=500), nullable=True),
        sa.Column(
            "dnssec", sa.String(length=16), nullable=False, server_default="unknown"
        ),
        sa.Column("caa", sa.JSON(), nullable=False),
        sa.Column("posture_issues", sa.JSON(), nullable=False),
        sa.Column("posture_checked", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("scan_id", "zone", name="uq_domain_posture_scan_zone"),
    )
    for column in ("scan_id", "target_id", "project_id", "zone"):
        op.create_index(f"ix_domain_posture_{column}", "domain_posture", [column])
    op.create_index(
        "ix_domain_posture_scan_discovered",
        "domain_posture",
        ["scan_id", "discovered_at"],
    )
    op.create_index(
        "ix_domain_posture_target_discovered",
        "domain_posture",
        ["target_id", "discovered_at"],
    )

    op.add_column("subdomains", sa.Column("posture_issues", sa.JSON(), nullable=True))
    op.add_column("subdomains", sa.Column("posture_checked", sa.JSON(), nullable=True))
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX} "
            "ON subdomains USING gin ((posture_issues::jsonb))"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX}")
    op.drop_column("subdomains", "posture_checked")
    op.drop_column("subdomains", "posture_issues")
    op.drop_table("domain_posture")
