"""domain posture: mail subdomains carry their own row under a parent zone

Revision ID: f7b3d9a24c81
Revises: e4a1c7b92d63
Create Date: 2026-09-15 06:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7b3d9a24c81"
down_revision: str | None = "e4a1c7b92d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "domain_posture", sa.Column("parent", sa.String(length=253), nullable=True)
    )
    op.add_column(
        "domain_posture",
        sa.Column(
            "dmarc_inherited", sa.Boolean(), nullable=False, server_default="false"
        ),
    )


def downgrade() -> None:
    op.drop_column("domain_posture", "dmarc_inherited")
    op.drop_column("domain_posture", "parent")
