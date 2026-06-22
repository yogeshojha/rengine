"""add subdomains (target_id, name, discovered_at) index for first-seen deltas

Revision ID: d5f7b9c1e3a4
Revises: c4e6a8b0d2f3
Create Date: 2026-06-22 12:00:00.000000+00:00

Supports the per-scan "newly discovered subdomains" computation (first-seen per
target/name) and the scan-history "what changed" aggregates without a full sort.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5f7b9c1e3a4"
down_revision: str | None = "c4e6a8b0d2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_subdomains_target_name_discovered "
        "ON subdomains (target_id, name, discovered_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_subdomains_target_name_discovered")
