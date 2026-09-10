"""query statistics, so a slow endpoint is measurable rather than hunted

Revision ID: e17b2c904af6
Revises: c3f7a1e05d92
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e17b2c904af6"
down_revision: str | None = "c3f7a1e05d92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# docker-compose preloads the library; an external Postgres without it must still migrate
CREATE = """
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'pg_stat_statements unavailable (%); query statistics are off', SQLERRM;
END
$$;
"""


def upgrade() -> None:
    op.execute(CREATE)


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_stat_statements")
