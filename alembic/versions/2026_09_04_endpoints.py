"""endpoints and endpoint_coverage: the fifth asset dimension

Revision ID: b8e3f52c1a70
Revises: d4a1c8b7e206
Create Date: 2026-09-04 17:10:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b8e3f52c1a70"
down_revision: str | None = "d4a1c8b7e206"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "endpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signature", sa.String(length=64), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
        sa.Column(
            "scheme", sa.String(length=8), nullable=False, server_default="https"
        ),
        sa.Column("path", sa.String(length=1500), nullable=False),
        sa.Column("dir_path", sa.String(length=1500), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("extension", sa.String(length=10), nullable=True),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("param_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("param_samples", sa.JSON(), nullable=False),
        sa.Column("variants", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "more_variants", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("methods", sa.JSON(), nullable=False),
        sa.Column("sources", sa.JSON(), nullable=False),
        sa.Column("primary_source", sa.String(length=24), nullable=False),
        sa.Column("discovery", sa.JSON(), nullable=False),
        sa.Column("found_on", sa.String(length=2000), nullable=True),
        sa.Column("is_probed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=1000), nullable=True),
        sa.Column("words", sa.Integer(), nullable=True),
        sa.Column("lines", sa.Integer(), nullable=True),
        sa.Column("response_time", sa.Float(), nullable=True),
        sa.Column("redirect_location", sa.String(length=2000), nullable=True),
        sa.Column("content_hash", sa.String(length=80), nullable=True),
        sa.Column("tech", sa.JSON(), nullable=False),
        sa.Column("endpoint_class", sa.String(length=16), nullable=False),
        sa.Column("interest", sa.JSON(), nullable=False),
        sa.Column("http_asset_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("subdomain_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("archive_last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "signature", name="uq_endpoint_scan_signature"),
    )
    for column in (
        "scan_id",
        "target_id",
        "project_id",
        "signature",
        "host",
        "dir_path",
        "extension",
        "depth",
        "param_count",
        "primary_source",
        "is_probed",
        "status_code",
        "content_hash",
        "endpoint_class",
        "http_asset_id",
        "subdomain_id",
        "discovered_at",
    ):
        op.create_index(f"ix_endpoints_{column}", "endpoints", [column])

    # the table's own working set: one scan's rows ordered the way the tree walks them
    op.create_index(
        "ix_endpoints_scan_dir", "endpoints", ["scan_id", "dir_path", "path"]
    )
    # is:new and the cross-scan delta
    op.create_index(
        "ix_endpoints_target_signature", "endpoints", ["target_id", "signature"]
    )
    # free-text branches keep their own index instead of a shared seq scan
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for column in ("url", "path", "title"):
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_endpoints_{column}_trgm "
            f"ON endpoints USING gin ({column} gin_trgm_ops)"
        )

    op.create_table(
        "endpoint_coverage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("tool", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("hosts_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hosts_scanned", sa.Integer(), nullable=True),
        sa.Column("hosts_dropped", sa.JSON(), nullable=False),
        sa.Column("urls_found", sa.Integer(), nullable=True),
        sa.Column("urls_stored", sa.Integer(), nullable=True),
        sa.Column("urls_probed", sa.Integer(), nullable=True),
        sa.Column("pages_fetched", sa.Integer(), nullable=True),
        sa.Column("depth_reached", sa.Integer(), nullable=True),
        sa.Column("errors", sa.Integer(), nullable=True),
        sa.Column("capped", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("cap_reason", sa.String(length=200), nullable=True),
        sa.Column("command", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("scan_id", "target_id", "project_id", "source"):
        op.create_index(f"ix_endpoint_coverage_{column}", "endpoint_coverage", [column])


def downgrade() -> None:
    op.drop_table("endpoint_coverage")
    for column in ("url", "path", "title"):
        op.execute(f"DROP INDEX IF EXISTS ix_endpoints_{column}_trgm")
    op.drop_table("endpoints")
