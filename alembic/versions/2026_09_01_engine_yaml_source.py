"""scan engines: keep the authored YAML document alongside the structured stages

Revision ID: e2b5d8c14f37
Revises: d1a4c7e02b95
Create Date: 2026-09-01 09:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2b5d8c14f37"
down_revision: str | None = "d1a4c7e02b95"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scan_engines", sa.Column("yaml_source", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_engines", "yaml_source")
