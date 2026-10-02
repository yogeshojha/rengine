"""drop stored ip_enrichment false from engines

Revision ID: d17b3c9e5f24
Revises: c84f2a6b1d93
Create Date: 2026-09-03 12:30:00.000000+00:00
"""

from collections.abc import Sequence

revision: str = "d17b3c9e5f24"
down_revision: str | None = "c84f2a6b1d93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
