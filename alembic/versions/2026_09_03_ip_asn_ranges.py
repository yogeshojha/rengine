"""ip -> asn/country range tables, and widen every asn column to bigint

Revision ID: c84f2a6b1d93
Revises: b73e91d5c4a8
Create Date: 2026-09-03 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET

from alembic import op

revision: str = "c84f2a6b1d93"
down_revision: str | None = "b73e91d5c4a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# AS numbers are unsigned 32-bit; integer overflows on any ASN above 2^31-1
_ASN_COLUMNS = (
    ("subdomains", "asn"),
    ("http_assets", "asn"),
    ("ip_addresses", "asn"),
    ("target_bgp_summaries", "asn"),
    ("ripestat_announced_prefixes", "asn"),
    ("ripestat_as_overviews", "asn"),
    ("ripestat_asn_neighbours", "asn"),
    ("ripestat_network_info", "asn"),
    ("ripestat_prefix_overviews", "asn"),
    ("ripestat_asn_neighbours", "neighbour_asn"),
    ("ripestat_related_prefixes", "origin_asn"),
)


def upgrade() -> None:
    op.create_table(
        "ip_asn_ranges",
        sa.Column("start_ip", INET(), primary_key=True, nullable=False),
        sa.Column("end_ip", INET(), nullable=False),
        sa.Column("asn", sa.BigInteger(), nullable=False),
        sa.Column("as_name", sa.String(length=255), nullable=True),
    )
    op.create_table(
        "ip_country_ranges",
        sa.Column("start_ip", INET(), primary_key=True, nullable=False),
        sa.Column("end_ip", INET(), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
    )
    for table, column in _ASN_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE bigint "
            f"USING {column}::bigint"
        )


def downgrade() -> None:
    for table, column in _ASN_COLUMNS:
        op.execute(
            f"ALTER TABLE {table} ALTER COLUMN {column} TYPE integer "
            f"USING {column}::integer"
        )
    op.drop_table("ip_country_ranges")
    op.drop_table("ip_asn_ranges")
