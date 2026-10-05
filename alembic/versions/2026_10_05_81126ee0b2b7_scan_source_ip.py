"""scan source ip

Revision ID: 81126ee0b2b7
Revises: f4644c5853ed
Create Date: 2026-10-05
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "81126ee0b2b7"
down_revision: str | None = "f4644c5853ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("source_ip", sa.JSON(), nullable=True))
    op.add_column(
        "instance_settings",
        sa.Column(
            "source_ip_lookups",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "source_ip_lookups")
    op.drop_column("scans", "source_ip")
