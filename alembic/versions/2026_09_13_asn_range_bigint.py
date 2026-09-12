"""widen the whois AS range columns to bigint

Revision ID: e6b40f2a9c17
Revises: d5a91c73e28f
Create Date: 2026-09-13 00:30:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e6b40f2a9c17"
down_revision: str | None = "d5a91c73e28f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("asn_range_start", "asn_range_end"):
        op.alter_column(
            "whois_records",
            column,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=True,
        )


def downgrade() -> None:
    for column in ("asn_range_start", "asn_range_end"):
        op.alter_column(
            "whois_records",
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=True,
        )
