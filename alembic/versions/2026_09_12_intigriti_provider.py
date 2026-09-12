"""intigriti api provider, program platform id and scope tier

Revision ID: a4f1c07b9d32
Revises: 9e4b7c31a2d6
Create Date: 2026-09-12 21:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a4f1c07b9d32"
down_revision: str | None = "9e4b7c31a2d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS 'INTIGRITI'")
    op.add_column(
        "bounty_programs",
        sa.Column("external_id", sa.String(length=100), nullable=True),
    )
    op.create_index(
        "ix_bounty_programs_external_id", "bounty_programs", ["external_id"]
    )
    op.add_column(
        "bounty_scopes", sa.Column("tier", sa.String(length=32), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("bounty_scopes", "tier")
    op.drop_index("ix_bounty_programs_external_id", table_name="bounty_programs")
    op.drop_column("bounty_programs", "external_id")
