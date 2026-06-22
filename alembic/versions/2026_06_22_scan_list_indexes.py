"""add composite indexes backing the scan list default sort

Revision ID: c4e6a8b0d2f3
Revises: b3d5f7a9c1e2
Create Date: 2026-06-22 11:00:00.000000+00:00

Backs the dominant scan-list query (project- and target-scoped, ordered by
coalesce(started_at, created_at) DESC, created_at DESC) so it serves from an
index instead of a full sort at scale.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c4e6a8b0d2f3"
down_revision: str | None = "b3d5f7a9c1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scans_project_started "
        "ON scans (project_id, (coalesce(started_at, created_at)) DESC, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_scans_target_started "
        "ON scans (target_id, (coalesce(started_at, created_at)) DESC, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_scans_target_started")
    op.execute("DROP INDEX IF EXISTS ix_scans_project_started")
