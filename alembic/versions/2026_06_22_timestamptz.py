"""convert all timestamp columns to timestamptz (store tz-aware UTC)

Revision ID: f7a1c3e5b9d2
Revises: a1c3e5f7b9d2
Create Date: 2026-06-22 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f7a1c3e5b9d2"
down_revision: str | None = "a1c3e5f7b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Convert every naive `timestamp` column to `timestamptz`, interpreting the
    # existing stored values as UTC. Production-grade: timestamps are stored
    # tz-aware so the API serializes ISO-8601 with offset (no client tz drift).
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp without time zone'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE timestamptz '
                    'USING %I AT TIME ZONE ''UTC''',
                    r.table_name, r.column_name, r.column_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
            FOR r IN
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND data_type = 'timestamp with time zone'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I ALTER COLUMN %I TYPE timestamp '
                    'USING %I AT TIME ZONE ''UTC''',
                    r.table_name, r.column_name, r.column_name
                );
            END LOOP;
        END $$;
        """
    )
