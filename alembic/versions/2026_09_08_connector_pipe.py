"""a connector is a pipe: scope moves to the moment of testing, not to the connection

Revision ID: a5d19c7e4b83
Revises: f2b8d3e64a17
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a5d19c7e4b83"
down_revision: str | None = "f2b8d3e64a17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "connectors",
        sa.Column(
            "only_known_hosts", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    # a connector that only kept known hosts keeps that behaviour
    op.execute(
        "UPDATE connectors SET only_known_hosts = true WHERE import_mode <> 'everything'"
    )
    op.drop_column("connectors", "import_mode")
    op.drop_column("connectors", "target_id")


def downgrade() -> None:
    op.add_column(
        "connectors",
        sa.Column(
            "import_mode",
            sa.String(length=16),
            nullable=False,
            server_default="in_scope",
        ),
    )
    op.add_column("connectors", sa.Column("target_id", sa.UUID(), nullable=True))
    op.execute(
        "UPDATE connectors SET import_mode = 'everything' WHERE only_known_hosts = false"
    )
    op.drop_column("connectors", "only_known_hosts")
