"""add subdomains.is_excluded

Revision ID: b3d5f7a9c1e2
Revises: f7a1c3e5b9d2
Create Date: 2026-06-22 01:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b3d5f7a9c1e2"
down_revision: str | None = "f7a1c3e5b9d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subdomains",
        sa.Column(
            "is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index(
        op.f("ix_subdomains_is_excluded"), "subdomains", ["is_excluded"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_subdomains_is_excluded"), table_name="subdomains")
    op.drop_column("subdomains", "is_excluded")
