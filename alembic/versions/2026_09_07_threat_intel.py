"""threat intel: EPSS scores, the KEV catalog, provider cache and per-finding signals

Revision ID: f3c7a1d84b26
Revises: e8a1c5d29f47
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f3c7a1d84b26"
down_revision: str | None = "e8a1c5d29f47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "epss_scores",
        sa.Column("cve", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("percentile", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("cve"),
    )

    op.create_table(
        "kev_entries",
        sa.Column("cve", sa.String(length=30), nullable=False),
        sa.Column("vendor", sa.String(length=200), nullable=True),
        sa.Column("product", sa.String(length=200), nullable=True),
        sa.Column("name", sa.String(length=500), nullable=True),
        sa.Column("short_description", sa.Text(), nullable=True),
        sa.Column("required_action", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cwes", sa.JSON(), nullable=False),
        sa.Column("known_ransomware", sa.Boolean(), nullable=False),
        sa.Column("date_added", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.PrimaryKeyConstraint("cve"),
    )
    op.create_index("ix_kev_entries_known_ransomware", "kev_entries", ["known_ransomware"])
    op.create_index("ix_kev_entries_date_added", "kev_entries", ["date_added"])

    op.create_table(
        "cve_intel",
        sa.Column("cve", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=False),
        sa.Column("pocs", sa.JSON(), nullable=False),
        sa.Column("poc_count", sa.Integer(), nullable=False),
        sa.Column("poc_first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("template_available", sa.Boolean(), nullable=True),
        sa.Column("is_remote", sa.Boolean(), nullable=True),
        sa.Column("needs_auth", sa.Boolean(), nullable=True),
        sa.Column("patch_available", sa.Boolean(), nullable=True),
        sa.Column("vendor_kev", sa.Boolean(), nullable=False),
        sa.Column("kev_sources", sa.JSON(), nullable=False),
        sa.Column("exposure_hosts", sa.BigInteger(), nullable=True),
        sa.Column("exposure_products", sa.JSON(), nullable=False),
        sa.Column("hackerone_rank", sa.Integer(), nullable=True),
        sa.Column("hackerone_reports", sa.Integer(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cve"),
    )
    op.create_index("ix_cve_intel_fetched_at", "cve_intel", ["fetched_at"])

    op.create_table(
        "threat_feeds",
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("kind"),
    )

    op.create_table(
        "intel_signals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("vulnerability_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vulnerability_id", "kind", name="uq_intel_signal_vuln_kind"),
    )
    op.create_index("ix_intel_signals_vulnerability_id", "intel_signals", ["vulnerability_id"])
    op.create_index("ix_intel_signals_scan_id", "intel_signals", ["scan_id"])
    op.create_index("ix_intel_signals_kind", "intel_signals", ["kind"])

    op.add_column("vulnerabilities", sa.Column("exploit_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("vulnerabilities", sa.Column("intel_kinds", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column(
        "vulnerabilities",
        sa.Column("kev_ransomware", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("vulnerabilities", sa.Column("kev_due_date", sa.Date(), nullable=True))
    op.add_column("vulnerabilities", sa.Column("poc_count", sa.Integer(), nullable=True))
    op.add_column("vulnerabilities", sa.Column("template_available", sa.Boolean(), nullable=True))
    op.add_column("vulnerabilities", sa.Column("intel_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_vulnerabilities_exploit_score", "vulnerabilities", ["exploit_score"])
    op.create_index("ix_vulnerabilities_kev_ransomware", "vulnerabilities", ["kev_ransomware"])


def downgrade() -> None:
    op.drop_index("ix_vulnerabilities_kev_ransomware", table_name="vulnerabilities")
    op.drop_index("ix_vulnerabilities_exploit_score", table_name="vulnerabilities")
    for col in (
        "intel_at",
        "template_available",
        "poc_count",
        "kev_due_date",
        "kev_ransomware",
        "intel_kinds",
        "exploit_score",
    ):
        op.drop_column("vulnerabilities", col)
    op.drop_table("intel_signals")
    op.drop_table("threat_feeds")
    op.drop_table("cve_intel")
    op.drop_table("kev_entries")
    op.drop_table("epss_scores")
