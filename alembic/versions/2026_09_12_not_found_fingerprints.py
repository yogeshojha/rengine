"""not-found fingerprints on web assets

Revision ID: d7b3f09a4e15
Revises: c4a7e21d8f03
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7b3f09a4e15"
down_revision: str | None = "c4a7e21d8f03"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("http_assets", sa.Column("not_found", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("http_assets", "not_found")
