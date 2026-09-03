"""asset query language: trigram indexes for every free-text searched column

Revision ID: b73e91d5c4a8
Revises: a91c4f7b2e05
Create Date: 2026-09-03 10:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b73e91d5c4a8"
down_revision: str | None = "a91c4f7b2e05"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGRAM = (
    ("ix_subdomains_org_trgm", "subdomains", "asn_org"),
    ("ix_subdomains_cdn_trgm", "subdomains", "cdn_name"),
    ("ix_subdomains_waf_trgm", "subdomains", "waf"),
    ("ix_subdomains_final_url_trgm", "subdomains", "final_url"),
    ("ix_subdomains_tech_text_trgm", "subdomains", "cast(tech as text)"),
    ("ix_subdomains_sources_text_trgm", "subdomains", "cast(sources as text)"),
    ("ix_subdomains_ips_text_trgm", "subdomains", "cast(resolved_ips as text)"),
    ("ix_http_assets_cert_cn_trgm", "http_assets", "tls_subject_cn"),
    ("ix_http_assets_cert_issuer_trgm", "http_assets", "tls_issuer"),
    ("ix_http_assets_sans_text_trgm", "http_assets", "cast(tls_sans as text)"),
    ("ix_http_assets_issuer_org_trgm", "http_assets", "tls_issuer_org"),
    ("ix_http_assets_issuer_cn_trgm", "http_assets", "tls_issuer_cn"),
    ("ix_http_assets_location_trgm", "http_assets", "location"),
)


def upgrade() -> None:
    for name, table, expression in _TRIGRAM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} "
            f"USING gin (({expression}) gin_trgm_ops)"
        )


def downgrade() -> None:
    for name, _table, _expression in _TRIGRAM:
        op.execute(f"DROP INDEX IF EXISTS {name}")
