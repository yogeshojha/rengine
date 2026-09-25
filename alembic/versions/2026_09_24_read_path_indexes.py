"""read-path indexes: screenshot rows by scan, drop low-cardinality single-column indexes

Revision ID: 2f7a9c4e1b60
Revises: 7a2e9c4b1f60
Create Date: 2026-09-24 18:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "2f7a9c4e1b60"
down_revision: str | None = "7a2e9c4b1f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCREENSHOTS = {
    "ix_subdomains_screenshot": "subdomains",
    "ix_http_assets_screenshot": "http_assets",
}
DROPPED = {
    "ix_software_cves_name": ("software_cves", "name"),
    "ix_software_cves_product": ("software_cves", "product"),
    "ix_software_cves_severity": ("software_cves", "severity"),
    "ix_software_cves_confidence": ("software_cves", "confidence"),
    "ix_software_cves_evidence": ("software_cves", "evidence"),
    "ix_software_cves_port": ("software_cves", "port"),
    "ix_endpoints_depth": ("endpoints", "depth"),
    "ix_endpoints_primary_source": ("endpoints", "primary_source"),
    "ix_endpoints_endpoint_class": ("endpoints", "endpoint_class"),
}


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table in SCREENSHOTS.items():
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                f"ON {table} (scan_id) WHERE screenshot_path IS NOT NULL"
            )
        for name in DROPPED:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, (table, column) in DROPPED.items():
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} ON {table} ({column})"
            )
        for name in SCREENSHOTS:
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
