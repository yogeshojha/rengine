"""capture raw http request/response + denormalize signal fields onto subdomains

Revision ID: b5d7f9a1c3e6
Revises: a4c6e8f0b2d4
Create Date: 2026-06-26 09:00:00.000000+00:00

Store the raw request, raw response headers, response body, parsed header map,
and a body preview on HttpAsset (httpx -irr). Denormalize the primary web
service's waf/asn/favicon/cert-expiry signals onto Subdomain so the Web Assets
table can render and filter them without a join.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "b5d7f9a1c3e6"
down_revision: str | None = "a4c6e8f0b2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STR = sqlmodel.sql.sqltypes.AutoString


def _col(name: str, type_: sa.types.TypeEngine, **kw) -> sa.Column:
    return sa.Column(name, type_, **kw)


_HTTP_COLUMNS = [
    _col("raw_request", sa.Text(), nullable=True),
    _col("raw_response_header", sa.Text(), nullable=True),
    _col("response_body", sa.Text(), nullable=True),
    _col("response_headers", sa.JSON(), nullable=False, server_default="{}"),
    _col("body_preview", _STR(length=512), nullable=True),
]

_SUBDOMAIN_COLUMNS = [
    _col("final_url", _STR(length=2000), nullable=True),
    _col("waf", _STR(length=100), nullable=True),
    _col("asn", sa.Integer(), nullable=True),
    _col("asn_org", _STR(length=255), nullable=True),
    _col("favicon_hash", _STR(length=64), nullable=True),
    _col("tls_not_after", sa.DateTime(timezone=True), nullable=True),
    _col("tls_expired", sa.Boolean(), nullable=True),
    _col("tls_self_signed", sa.Boolean(), nullable=True),
]


def upgrade() -> None:
    for col in _HTTP_COLUMNS:
        op.add_column("http_assets", col)
    for col in _SUBDOMAIN_COLUMNS:
        op.add_column("subdomains", col)


def downgrade() -> None:
    for col in reversed(_SUBDOMAIN_COLUMNS):
        op.drop_column("subdomains", col.name)
    for col in reversed(_HTTP_COLUMNS):
        op.drop_column("http_assets", col.name)
