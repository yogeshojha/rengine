"""name the ports an earlier scan left blank, from the IANA registry

Revision ID: b8f3d02a5c17
Revises: a4c7e91b2d63
Create Date: 2026-09-04 03:10:00.000000+00:00
"""

from collections.abc import Sequence

revision: str = "b8f3d02a5c17"
down_revision: str | None = "a4c7e91b2d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
