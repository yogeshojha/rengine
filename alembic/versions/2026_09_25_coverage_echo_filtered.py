"""vulnerability_coverage.echo_filtered

Revision ID: fe47e3eef6a7
Revises: 7b3e9d1c5a42
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "fe47e3eef6a7"
down_revision: str | None = "7b3e9d1c5a42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vulnerability_coverage",
        sa.Column("echo_filtered", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("vulnerability_coverage", "echo_filtered")
