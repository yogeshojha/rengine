"""btree over (scan_id, matched_at) so corroboration lookups stop probing the trigram index

Revision ID: d4a1c8b7e206
Revises: c2e7a4f19b83
Create Date: 2026-09-04 16:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4a1c8b7e206"
down_revision: str | None = "c2e7a4f19b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEX = "ix_vulnerabilities_scan_matched"


def upgrade() -> None:
    op.execute(
        f"CREATE INDEX IF NOT EXISTS {_INDEX} "
        "ON vulnerabilities USING btree (scan_id, matched_at)"
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
