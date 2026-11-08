"""drop the per-row cascades from interest signals and endpoint responses

Revision ID: c7d8e9f0a1b2
Revises: b6c7d8e9f0a1
Create Date: 2026-11-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c7d8e9f0a1b2"
down_revision: str | None = "b6c7d8e9f0a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

KEYS = (
    (
        "interest_signals",
        "interest_signals_subdomain_id_fkey",
        "subdomain_id",
        "subdomains",
    ),
    (
        "endpoint_responses",
        "endpoint_responses_endpoint_id_fkey",
        "endpoint_id",
        "endpoints",
    ),
)
ORPHANS = (
    "DELETE FROM interest_signals t WHERE NOT EXISTS "
    "(SELECT 1 FROM subdomains p WHERE p.id = t.subdomain_id)",
    "DELETE FROM endpoint_responses t WHERE NOT EXISTS "
    "(SELECT 1 FROM endpoints p WHERE p.id = t.endpoint_id)",
)


def upgrade() -> None:
    for table, name, _column, _parent in KEYS:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT {name}")


def downgrade() -> None:
    for statement in ORPHANS:
        op.execute(statement)
    for table, name, column, parent in KEYS:
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {name} FOREIGN KEY ({column}) "
            f"REFERENCES {parent} (id) ON DELETE CASCADE"
        )
