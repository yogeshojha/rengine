"""add scan activity event enum values

Revision ID: a1c3e5f7b9d2
Revises: f3b7d1a9c2e4
Create Date: 2026-06-21 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "a1c3e5f7b9d2"
down_revision: str | None = "f3b7d1a9c2e4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# activity_logs.event_type is a native pg enum; names match ActivityEvent members.
_NEW_VALUES = ("SCAN_STARTED", "SCAN_PROGRESS", "SCAN_COMPLETED", "SCAN_FAILED")


def upgrade() -> None:
    for value in _NEW_VALUES:
        op.execute(f"ALTER TYPE activityevent ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres cannot drop enum values without recreating the type; leave as-is.
    pass
