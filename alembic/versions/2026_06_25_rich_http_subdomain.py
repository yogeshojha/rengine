"""enrich http_assets + denormalize primary HTTP summary onto subdomains

Revision ID: a4c6e8f0b2d4
Revises: f1a3c5e7d9b2
Create Date: 2026-06-25 17:00:00.000000+00:00

Capture the full httpx field set (method/path/chain/response-time/words/lines/
cpe/http2/all-IPs/richer-TLS) on HttpAsset, and denormalize the primary web
service summary onto Subdomain for the 2.x-style table.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "a4c6e8f0b2d4"
down_revision: str | None = "f1a3c5e7d9b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STR = sqlmodel.sql.sqltypes.AutoString


def _col(name: str, type_: sa.types.TypeEngine, **kw) -> sa.Column:
    return sa.Column(name, type_, **kw)


_HTTP_COLUMNS = [
    _col("method", _STR(length=10), nullable=True),
    _col("path", _STR(length=2000), nullable=True),
    _col("chain_status_codes", sa.JSON(), nullable=False, server_default="[]"),
    _col("response_time", sa.Float(), nullable=True),
    _col("words", sa.Integer(), nullable=True),
    _col("lines", sa.Integer(), nullable=True),
    _col("cpe", sa.JSON(), nullable=False, server_default="[]"),
    _col("favicon_path", _STR(length=2000), nullable=True),
    _col("header_hash", _STR(length=80), nullable=True),
    _col("supports_http2", sa.Boolean(), nullable=False, server_default=sa.false()),
    _col("supports_pipeline", sa.Boolean(), nullable=False, server_default=sa.false()),
    _col("a_records", sa.JSON(), nullable=False, server_default="[]"),
    _col("aaaa_records", sa.JSON(), nullable=False, server_default="[]"),
    _col("cdn_type", _STR(length=20), nullable=True),
    _col("tls_cipher", _STR(length=100), nullable=True),
    _col("tls_subject_dn", _STR(length=1000), nullable=True),
    _col("tls_issuer_cn", _STR(length=500), nullable=True),
    _col("tls_issuer_org", _STR(length=500), nullable=True),
    _col("tls_serial", _STR(length=200), nullable=True),
    _col("tls_fingerprint", _STR(length=80), nullable=True),
    _col("tls_not_before", sa.DateTime(timezone=True), nullable=True),
]

_SUBDOMAIN_COLUMNS = [
    _col("is_important", sa.Boolean(), nullable=False, server_default=sa.false()),
    _col("http_url", _STR(length=2000), nullable=True),
    _col("http_status", sa.Integer(), nullable=True),
    _col("page_title", _STR(length=1000), nullable=True),
    _col("content_type", _STR(length=255), nullable=True),
    _col("content_length", sa.Integer(), nullable=True),
    _col("response_time", sa.Float(), nullable=True),
    _col("webserver", _STR(length=255), nullable=True),
    _col("tech", sa.JSON(), nullable=False, server_default="[]"),
    _col("is_cdn", sa.Boolean(), nullable=False, server_default=sa.false()),
    _col("cdn_name", _STR(length=100), nullable=True),
    _col("screenshot_path", _STR(length=500), nullable=True),
]


def upgrade() -> None:
    for col in _HTTP_COLUMNS:
        op.add_column("http_assets", col)
    op.create_index(op.f("ix_http_assets_ip"), "http_assets", ["ip"], unique=False)

    for col in _SUBDOMAIN_COLUMNS:
        op.add_column("subdomains", col)
    op.create_index(
        op.f("ix_subdomains_http_status"), "subdomains", ["http_status"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subdomains_http_status"), table_name="subdomains")
    for col in reversed(_SUBDOMAIN_COLUMNS):
        op.drop_column("subdomains", col.name)

    op.drop_index(op.f("ix_http_assets_ip"), table_name="http_assets")
    for col in reversed(_HTTP_COLUMNS):
        op.drop_column("http_assets", col.name)
