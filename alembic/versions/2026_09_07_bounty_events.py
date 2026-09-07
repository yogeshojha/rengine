"""bounty_events: what changed in a program since the last sync

Revision ID: a2d64f8b31c7
Revises: f7c3a5e18b92
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a2d64f8b31c7"
down_revision: str | None = "f7c3a5e18b92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bounty_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("handle", sa.String(length=200), nullable=False),
        sa.Column("program_name", sa.String(length=300), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("asset_type", sa.String(length=48), nullable=True),
        sa.Column("asset_identifier", sa.String(length=1000), nullable=True),
        sa.Column("detail", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"], ["bounty_programs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bounty_events_id", "bounty_events", ["id"])
    op.create_index("ix_bounty_events_platform", "bounty_events", ["platform"])
    op.create_index("ix_bounty_events_program_id", "bounty_events", ["program_id"])
    op.create_index("ix_bounty_events_handle", "bounty_events", ["handle"])
    op.create_index("ix_bounty_events_kind", "bounty_events", ["kind"])
    op.create_index("ix_bounty_events_created_at", "bounty_events", ["created_at"])

    op.add_column(
        "instance_settings",
        sa.Column(
            "bounty_sync_interval",
            sa.String(length=16),
            nullable=False,
            server_default="daily",
        ),
    )
    op.add_column(
        "instance_settings",
        sa.Column("bounty_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "instance_settings",
        sa.Column("bounty_events_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "bounty_events_seen_at")
    op.drop_column("instance_settings", "bounty_synced_at")
    op.drop_column("instance_settings", "bounty_sync_interval")
    op.drop_table("bounty_events")
