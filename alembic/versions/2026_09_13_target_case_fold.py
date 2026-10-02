"""case-fold target values

Revision ID: d5a91c73e28f
Revises: c93e5a7f0b41
Create Date: 2026-09-13 00:10:00.000000+00:00

"""

from collections.abc import Sequence

revision: str = "d5a91c73e28f"
down_revision: str | None = "c93e5a7f0b41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
