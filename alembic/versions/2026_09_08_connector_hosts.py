"""connector_hosts: every hostname a connector reached, so unknown domains can be offered as targets

Revision ID: e7a4c1d9b520
Revises: d41c7b9e2a10
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "e7a4c1d9b520"
down_revision: str | None = "d41c7b9e2a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_hosts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column(
            "registrable", sa.String(length=500), nullable=False, server_default=""
        ),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dismissed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("connector_id", "host", name="uq_connector_host"),
    )
    for column in (
        "connector_id",
        "project_id",
        "host",
        "registrable",
        "target_id",
        "dismissed",
        "last_seen_at",
    ):
        op.create_index(f"ix_connector_hosts_{column}", "connector_hosts", [column])

    op.add_column(
        "connectors",
        sa.Column("record_hosts", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    op.drop_column("connectors", "record_hosts")
    op.drop_table("connector_hosts")
