"""scan_engines.transport_overrides

Revision ID: a1f4c7d20e93
Revises: 3c8e2b7f41a9
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1f4c7d20e93"
down_revision: str | None = "3c8e2b7f41a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scan_engines",
        sa.Column(
            "transport_overrides",
            sa.JSON(),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    op.drop_column("scan_engines", "transport_overrides")
