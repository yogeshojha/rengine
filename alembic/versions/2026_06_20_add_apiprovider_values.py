"""add apiprovider enum values

Revision ID: b8d2f0a1c4e5
Revises: a7c1e9f2b3d4
Create Date: 2026-06-20 00:30:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8d2f0a1c4e5"
down_revision: str | None = "a7c1e9f2b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# New onboarding integration providers reuse the existing api_keys table whose
# provider column is a native pg enum. Names match the Python enum MEMBER names.
_NEW_VALUES = ("CHAOS", "NETLAS", "SECURITYTRAILS", "HACKERONE")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE apiprovider ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres cannot drop enum values without recreating the type; leave as-is.
    pass
