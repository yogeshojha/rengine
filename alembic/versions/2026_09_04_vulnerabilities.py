"""vulnerability findings, review state, coverage accounting and the template library

Revision ID: c2e7a4f19b83
Revises: b8f3d02a5c17
Create Date: 2026-09-04 15:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from shared.definitions.vulnerabilities import (
    CoverageStatus,
    Protocol,
    Scanner,
    Severity,
    TemplateOrigin,
    VulnState,
)

revision: str = "c2e7a4f19b83"
down_revision: str | None = "b8f3d02a5c17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGRAM = (
    ("ix_vulnerabilities_name_trgm", "vulnerabilities", "template_name"),
    ("ix_vulnerabilities_template_trgm", "vulnerabilities", "template_id"),
    ("ix_vulnerabilities_matched_trgm", "vulnerabilities", "matched_at"),
    ("ix_vulnerabilities_host_trgm", "vulnerabilities", "host"),
    ("ix_vuln_templates_name_trgm", "vuln_templates", "name"),
    ("ix_vuln_templates_template_trgm", "vuln_templates", "template_id"),
)

_JSON_GIN = (
    ("ix_vulnerabilities_tags_gin", "vulnerabilities", "tags"),
    ("ix_vulnerabilities_cve_gin", "vulnerabilities", "cve_ids"),
    ("ix_vuln_templates_tags_gin", "vuln_templates", "tags"),
)


def _json(name: str) -> sa.Column:
    return sa.Column(name, postgresql.JSON(astext_type=sa.Text()), nullable=False)


def upgrade() -> None:
    op.create_table(
        "vulnerabilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "scanner",
            sa.String(length=32),
            nullable=False,
            server_default=Scanner.NUCLEI.value,
        ),
        sa.Column("template_id", sa.String(length=200), nullable=False),
        sa.Column("template_name", sa.String(length=500), nullable=False),
        sa.Column("template_path", sa.String(length=500), nullable=True),
        sa.Column("template_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "severity",
            sa.String(length=16),
            nullable=False,
            server_default=Severity.UNKNOWN.value,
        ),
        sa.Column(
            "protocol",
            sa.String(length=16),
            nullable=False,
            server_default=Protocol.OTHER.value,
        ),
        sa.Column("matcher_name", sa.String(length=200), nullable=True),
        sa.Column("extractor_name", sa.String(length=200), nullable=True),
        _json("extracted_results"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("impact", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        _json("references"),
        _json("tags"),
        _json("authors"),
        _json("cve_ids"),
        _json("cwe_ids"),
        sa.Column("cvss_metrics", sa.String(length=200), nullable=True),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("epss_score", sa.Float(), nullable=True),
        sa.Column("epss_percentile", sa.Float(), nullable=True),
        sa.Column("cpe", sa.String(length=300), nullable=True),
        sa.Column(
            "is_kev", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        _json("extra"),
        sa.Column("matched_at", sa.String(length=2000), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("scheme", sa.String(length=16), nullable=True),
        sa.Column("url", sa.String(length=2000), nullable=True),
        sa.Column("path", sa.String(length=2000), nullable=True),
        sa.Column("subdomain_id", sa.Uuid(), nullable=True),
        sa.Column("http_asset_id", sa.Uuid(), nullable=True),
        sa.Column("port_id", sa.Uuid(), nullable=True),
        sa.Column("request", sa.Text(), nullable=True),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("curl_command", sa.Text(), nullable=True),
        _json("interaction"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "fingerprint", name="uq_vuln_scan_fingerprint"),
    )
    for column in (
        "id",
        "scan_id",
        "target_id",
        "project_id",
        "fingerprint",
        "scanner",
        "template_id",
        "severity",
        "protocol",
        "is_kev",
        "host",
        "ip",
        "port",
        "subdomain_id",
        "http_asset_id",
        "port_id",
        "discovered_at",
    ):
        op.create_index(
            f"ix_vulnerabilities_{column}", "vulnerabilities", [column], unique=False
        )
    op.execute(
        "CREATE INDEX ix_vulnerabilities_scan_severity ON vulnerabilities "
        "(scan_id, severity, template_id)"
    )

    op.create_table(
        "vulnerability_triage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("template_id", sa.String(length=200), nullable=False),
        sa.Column("matched_at", sa.String(length=2000), nullable=False),
        sa.Column(
            "state",
            sa.String(length=20),
            nullable=False,
            server_default=VulnState.OPEN.value,
        ),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_id", "fingerprint", name="uq_vulntriage_target_fp"),
    )
    for column in ("id", "project_id", "target_id", "fingerprint", "state"):
        op.create_index(
            f"ix_vulnerability_triage_{column}",
            "vulnerability_triage",
            [column],
            unique=False,
        )

    op.create_table(
        "vulnerability_coverage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column(
            "scanner",
            sa.String(length=32),
            nullable=False,
            server_default=Scanner.NUCLEI.value,
        ),
        sa.Column("group", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=CoverageStatus.COMPLETED.value,
        ),
        _json("severities"),
        _json("template_sets"),
        sa.Column("templates_selected", sa.Integer(), nullable=True),
        sa.Column("templates_loaded", sa.Integer(), nullable=True),
        sa.Column(
            "custom_templates", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("hosts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hosts_scanned", sa.Integer(), nullable=True),
        _json("hosts_dropped"),
        sa.Column("requests_sent", sa.Integer(), nullable=True),
        sa.Column("requests_planned", sa.Integer(), nullable=True),
        sa.Column("matched", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Integer(), nullable=True),
        sa.Column("rate_limit", sa.Integer(), nullable=True),
        sa.Column("concurrency", sa.Integer(), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("id", "scan_id", "target_id", "project_id"):
        op.create_index(
            f"ix_vulnerability_coverage_{column}",
            "vulnerability_coverage",
            [column],
            unique=False,
        )

    op.create_table(
        "vuln_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "origin",
            sa.String(length=16),
            nullable=False,
            server_default=TemplateOrigin.OFFICIAL.value,
        ),
        sa.Column("template_id", sa.String(length=200), nullable=False),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column(
            "severity",
            sa.String(length=16),
            nullable=False,
            server_default=Severity.UNKNOWN.value,
        ),
        sa.Column(
            "protocol",
            sa.String(length=16),
            nullable=False,
            server_default=Protocol.OTHER.value,
        ),
        sa.Column("directory", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        _json("tags"),
        _json("authors"),
        _json("references"),
        _json("cve_ids"),
        _json("cwe_ids"),
        sa.Column("cvss_score", sa.Float(), nullable=True),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("digest", sa.String(length=64), nullable=False, server_default=""),
        sa.Column("raw", sa.Text(), nullable=True),
        sa.Column(
            "enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("origin", "path", name="uq_vulntemplate_origin_path"),
    )
    for column in (
        "id",
        "origin",
        "template_id",
        "severity",
        "protocol",
        "directory",
        "enabled",
    ):
        op.create_index(
            f"ix_vuln_templates_{column}", "vuln_templates", [column], unique=False
        )

    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, column in _TRIGRAM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} "
            f"USING gin ({column} gin_trgm_ops)"
        )
    for name, table, column in _JSON_GIN:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} "
            f"USING gin (cast({column} AS jsonb))"
        )


def downgrade() -> None:
    for name, _table, _column in (*_TRIGRAM, *_JSON_GIN):
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.drop_table("vuln_templates")
    op.drop_table("vulnerability_coverage")
    op.drop_table("vulnerability_triage")
    op.execute("DROP INDEX IF EXISTS ix_vulnerabilities_scan_severity")
    op.drop_table("vulnerabilities")
