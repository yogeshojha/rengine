"""connector_actions: work reNgine hands back to the proxy, delivered once

Revision ID: f2b8d3e64a17
Revises: e7a4c1d9b520
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f2b8d3e64a17"
down_revision: str | None = "e7a4c1d9b520"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "connector_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind", sa.String(length=16), nullable=False, server_default="repeater"
        ),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False, server_default="GET"),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_connector_actions_connector_id", "connector_actions", ["connector_id"]
    )
    op.create_index(
        "ix_connector_actions_created_at", "connector_actions", ["created_at"]
    )
    op.create_index(
        "ix_connector_actions_delivered_at", "connector_actions", ["delivered_at"]
    )


def downgrade() -> None:
    op.drop_table("connector_actions")
