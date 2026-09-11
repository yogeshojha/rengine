"""a primary key is already an index, so the second one on id is write cost for nothing

Revision ID: b4c81e77a250
Revises: e17b2c904af6
Create Date: 2026-09-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b4c81e77a250"
down_revision: str | None = "e17b2c904af6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DROP = """
DO $$
DECLARE
    victim record;
BEGIN
    FOR victim IN
        SELECT c.relname AS index_name
        FROM pg_index i
        JOIN pg_class c ON c.oid = i.indexrelid
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND NOT i.indisprimary
          AND NOT i.indisunique
          AND i.indnatts = 1
          AND pg_get_indexdef(i.indexrelid) LIKE '%USING btree (id)%'
          AND EXISTS (
              SELECT 1 FROM pg_index p
              WHERE p.indrelid = i.indrelid AND p.indisprimary
          )
    LOOP
        EXECUTE format('DROP INDEX IF EXISTS public.%I', victim.index_name);
    END LOOP;
END
$$;
"""


def upgrade() -> None:
    op.execute(DROP)


def downgrade() -> None:
    # deliberately not recreated: the primary key serves every lookup they served
    pass
