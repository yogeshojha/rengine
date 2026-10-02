"""big int

Revision ID: c359e17eba19
Revises: e1be90b7d53b
Create Date: 2026-02-10 16:53:42.828468+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c359e17eba19"
down_revision: str | None = "e1be90b7d53b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "dns_records",
        "soa_serial",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "dns_records",
        "soa_serial",
        existing_type=sa.BigInteger(),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )
