"""api key provider: vulnx

Revision ID: a41d7e93c05b
Revises: f3c7a1d84b26
Create Date: 2026-09-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = "a41d7e93c05b"
down_revision: str | None = "f3c7a1d84b26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS 'VULNX'")


def downgrade() -> None:
    """Postgres cannot drop an enum value; the row filter is the guard."""
