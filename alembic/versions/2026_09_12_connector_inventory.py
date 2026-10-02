"""connector inventory: endpoint shapes, no scan triggers, no sessions

Revision ID: e52a8c1d7b30
Revises: b93d4e17c5a2
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e52a8c1d7b30"
down_revision: str | None = "b93d4e17c5a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("connector_sessions")
    for column in (
        "sync_trigger",
        "quiet_minutes",
        "queue_threshold",
        "capture_sessions",
    ):
        op.drop_column("connectors", column)

    op.add_column(
        "endpoints",
        sa.Column("shape", sa.String(length=1500), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_endpoints_project_host_shape", "endpoints", ["project_id", "host", "shape"]
    )


def downgrade() -> None:
    op.add_column(
        "connectors",
        sa.Column(
            "capture_sessions", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "connectors",
        sa.Column("queue_threshold", sa.Integer(), nullable=False, server_default="25"),
    )
    op.add_column(
        "connectors",
        sa.Column("quiet_minutes", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "connectors",
        sa.Column(
            "sync_trigger",
            sa.String(length=16),
            nullable=False,
            server_default="manual",
        ),
    )
    op.create_table(
        "connector_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client", sa.String(length=120), nullable=True),
        sa.Column("hosts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("novel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_index("ix_endpoints_project_host_shape", table_name="endpoints")
    op.drop_column("endpoints", "shape")
