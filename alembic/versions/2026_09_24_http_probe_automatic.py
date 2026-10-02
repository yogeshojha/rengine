"""HTTP probe runs automatically: drop its switch, move the every-port setting to port scan.

Revision ID: c8e4f2a7d913
Revises: 5d0c2a9e7b41
Create Date: 2026-09-24
"""

revision: str = "c8e4f2a7d913"
down_revision: str | None = "5d0c2a9e7b41"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
