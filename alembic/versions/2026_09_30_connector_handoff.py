"""connector_actions carry the request; connectors may restore a run's credentials

Revision ID: c3e8a1f47b92
Revises: b8e3d5f0a241
Create Date: 2026-09-30
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3e8a1f47b92"
down_revision: str | None = "b8e3d5f0a241"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("connector_actions", sa.Column("request", sa.Text(), nullable=True))
    op.add_column("connector_actions", sa.Column("response", sa.Text(), nullable=True))
    op.add_column("connector_actions", sa.Column("notes", sa.Text(), nullable=True))
    op.add_column(
        "connector_actions", sa.Column("color", sa.String(length=16), nullable=True)
    )
    op.add_column("connector_actions", sa.Column("scan_id", sa.Uuid(), nullable=True))
    op.add_column(
        "connectors",
        sa.Column(
            "restore_credentials",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("connectors", "restore_credentials")
    for name in ("scan_id", "color", "notes", "response", "request"):
        op.drop_column("connector_actions", name)
