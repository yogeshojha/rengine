"""software inference: nvd corpus, inferred cves, per-asset software

Revision ID: a7c3e91f2b48
Revises: f2a7c9d41b3e
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a7c3e91f2b48"
down_revision: str | None = "f2a7c9d41b3e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "nvd_cves",
        sa.Column("cve", sa.String(length=30), primary_key=True),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("cvss_vector", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_modified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_nvd_cves_severity", "nvd_cves", ["severity"])
    op.create_index("ix_nvd_cves_published_at", "nvd_cves", ["published_at"])

    op.create_table(
        "nvd_cpe_matches",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cve", sa.String(length=30), nullable=False),
        sa.Column("vendor", sa.String(length=200), nullable=False),
        sa.Column("product", sa.String(length=200), nullable=False),
        sa.Column("version_kind", sa.String(length=1), nullable=False),
        sa.Column("exact_key", sa.String(length=160), nullable=True),
        sa.Column("start_key", sa.String(length=160), nullable=True),
        sa.Column(
            "start_incl", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("end_key", sa.String(length=160), nullable=True),
        sa.Column("end_incl", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "conditional", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index("ix_nvd_cpe_matches_cve", "nvd_cpe_matches", ["cve"])
    op.create_index(
        "ix_nvd_cpe_matches_lookup",
        "nvd_cpe_matches",
        ["product", "version_kind", "vendor"],
    )

    op.create_table(
        "software_cves",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("cve", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("vendor", sa.String(length=200), nullable=False),
        sa.Column("product", sa.String(length=200), nullable=False),
        sa.Column("cpe", sa.String(length=300), nullable=False),
        sa.Column("version_source", sa.String(length=16), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column("epss_percentile", sa.Float(), nullable=True),
        sa.Column("is_kev", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "kev_ransomware", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("kev_due_date", sa.Date(), nullable=True),
        sa.Column("exploit_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("intel_kinds", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.String(length=16), nullable=False),
        sa.Column("caveats", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("host", sa.String(length=500), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("http_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("port_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "scan_id", "fingerprint", name="uq_software_scan_fingerprint"
        ),
    )
    for column in (
        "scan_id",
        "target_id",
        "project_id",
        "cve",
        "severity",
        "is_kev",
        "exploit_score",
        "confidence",
        "name",
        "product",
        "host",
        "ip",
        "port",
        "http_asset_id",
        "port_id",
        "fingerprint",
        "discovered_at",
    ):
        op.create_index(f"ix_software_cves_{column}", "software_cves", [column])
    op.create_index(
        "ix_software_cves_scan_discovered",
        "software_cves",
        ["scan_id", "discovered_at"],
    )
    op.create_index(
        "ix_software_cves_target_discovered",
        "software_cves",
        ["target_id", "discovered_at"],
    )
    op.create_index(
        "ix_software_cves_target_key_discovered",
        "software_cves",
        ["target_id", "fingerprint", "discovered_at"],
    )
    op.execute(
        "ALTER TABLE software_cves SET "
        "(autovacuum_analyze_scale_factor = 0.02, autovacuum_vacuum_scale_factor = 0.05)"
    )

    op.add_column(
        "http_assets",
        sa.Column("software", sa.JSON(), nullable=False, server_default="[]"),
    )

    # a Server header states the version inside the product string
    op.execute(
        r"""
        UPDATE ports
           SET version = substring(product from '^[^/\s]+/(\d[\w.+\-]*)'),
               product = substring(product from '^([^/\s]+)')
         WHERE product IS NOT NULL
           AND (version IS NULL OR version = '')
           AND product ~ '^[^/\s]+/\d'
        """
    )


def downgrade() -> None:
    op.drop_column("http_assets", "software")
    op.drop_table("software_cves")
    op.drop_table("nvd_cpe_matches")
    op.drop_table("nvd_cves")
