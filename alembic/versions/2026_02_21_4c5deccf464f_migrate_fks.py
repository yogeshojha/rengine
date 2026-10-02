"""migrate fks

Revision ID: 4c5deccf464f
Revises: 32af52b2b23b
Create Date: 2026-02-21 16:07:24.940907+00:00

"""

from collections.abc import Sequence

revision: str = "4c5deccf464f"
down_revision: str | None = "32af52b2b23b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
