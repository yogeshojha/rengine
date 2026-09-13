"""endpoints.host is a free-text field and needs its trigram index

Revision ID: c7e41d9a2f60
Revises: f2a7c93e1b48
Create Date: 2026-09-13 12:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7e41d9a2f60"
down_revision: str | None = "f2a7c93e1b48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_endpoints_host_trgm ON endpoints "
        "USING gin (host gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_endpoints_host_trgm")
