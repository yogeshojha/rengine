"""asset query language: trigram + full-text indexes for web asset search

Revision ID: a91c4f7b2e05
Revises: f4a6c8e0b2d1
Create Date: 2026-09-03 09:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op
from shared.models.http_asset import SEARCH_TSV_SQL

revision: str = "a91c4f7b2e05"
down_revision: str | None = "f4a6c8e0b2d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGRAM = (
    ("ix_subdomains_name_trgm", "subdomains", "name"),
    ("ix_subdomains_title_trgm", "subdomains", "page_title"),
    ("ix_subdomains_webserver_trgm", "subdomains", "webserver"),
    ("ix_subdomains_cname_trgm", "subdomains", "cname"),
    ("ix_http_assets_title_trgm", "http_assets", "title"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, column in _TRIGRAM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} "
            f"USING gin ({column} gin_trgm_ops)"
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subdomains_scan_status_name "
        "ON subdomains (scan_id, http_status, name)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_http_assets_scan_host "
        "ON http_assets (scan_id, host)"
    )
    op.execute(
        "ALTER TABLE http_assets ADD COLUMN IF NOT EXISTS search_tsv tsvector "
        f"GENERATED ALWAYS AS ({SEARCH_TSV_SQL}) STORED"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_http_assets_search_tsv "
        "ON http_assets USING gin (search_tsv)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_http_assets_search_tsv")
    op.execute("ALTER TABLE http_assets DROP COLUMN IF EXISTS search_tsv")
    op.execute("DROP INDEX IF EXISTS ix_http_assets_scan_host")
    op.execute("DROP INDEX IF EXISTS ix_subdomains_scan_status_name")
    for name, _table, _column in _TRIGRAM:
        op.execute(f"DROP INDEX IF EXISTS {name}")
