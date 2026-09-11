"""a self-hosted OAST server's token is a secret like any other key

Revision ID: d27c6a90f1b3
Revises: c19a5f3b7d84
Create Date: 2026-09-11
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d27c6a90f1b3"
down_revision: str | None = "c19a5f3b7d84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS 'INTERACTSH'")


def downgrade() -> None:
    pass
