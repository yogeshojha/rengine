"""vulnerabilities: bounty activity denormalised for the findings row

Revision ID: c93b12f4a8d5
Revises: b62f04a1d7e9
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c93b12f4a8d5"
down_revision: str | None = "b62f04a1d7e9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vulnerabilities", sa.Column("hackerone_reports", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("vulnerabilities", "hackerone_reports")
