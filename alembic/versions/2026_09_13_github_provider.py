"""github api key provider

Revision ID: f1a9c62d7b34
Revises: e5c2f8b41d93
Create Date: 2026-09-13 13:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f1a9c62d7b34"
down_revision: str | None = "e5c2f8b41d93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS 'GITHUB'")


def downgrade() -> None:
    # postgres cannot drop an enum value without recreating the type
    pass
