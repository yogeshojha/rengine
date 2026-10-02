"""indexes for server-side scan-results queries at 100k+ rows

Revision ID: c7e9f1b3d5a8
Revises: b5d7f9a1c3e6
Create Date: 2026-06-26 12:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c7e9f1b3d5a8"
down_revision: str | None = "b5d7f9a1c3e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BTREE = [
    ("ix_subdomains_scan_favicon", "subdomains", ["scan_id", "favicon_hash"]),
    ("ix_subdomains_scan_cname", "subdomains", ["scan_id", "cname"]),
    ("ix_subdomains_scan_asn", "subdomains", ["scan_id", "asn"]),
    ("ix_subdomains_scan_tls_after", "subdomains", ["scan_id", "tls_not_after"]),
    ("ix_http_assets_scan_fp", "http_assets", ["scan_id", "tls_fingerprint"]),
]
_GIN = [
    ("ix_subdomains_tech_gin", "subdomains", "tech"),
    ("ix_subdomains_sources_gin", "subdomains", "sources"),
    ("ix_subdomains_ips_gin", "subdomains", "resolved_ips"),
]


def upgrade() -> None:
    for name, table, cols in _BTREE:
        op.create_index(name, table, cols, unique=False)
    for name, table, col in _GIN:
        op.create_index(
            name, table, [sa.text(f"(({col})::jsonb)")], postgresql_using="gin"
        )


def downgrade() -> None:
    for name, _table, _col in _GIN:
        op.drop_index(name, table_name="subdomains")
    for name, table, _cols in reversed(_BTREE):
        op.drop_index(name, table_name=table)
