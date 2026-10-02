"""web hygiene: re-evaluate stored responses for the internal address check

Revision ID: 8d2b6f0a4c13
Revises: 3c9e5a1f7d24
Create Date: 2026-09-24
"""

from collections.abc import Sequence

revision: str = "8d2b6f0a4c13"
down_revision: str | None = "3c9e5a1f7d24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
