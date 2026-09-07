"""bounty programs from the public feed: source, payout and platform facts

Revision ID: b93f27c05ea8
Revises: c8e35a71d904
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b93f27c05ea8"
down_revision: str | None = "c8e35a71d904"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bounty_programs",
        sa.Column("source", sa.String(length=16), nullable=False, server_default="api"),
    )
    op.create_index("ix_bounty_programs_source", "bounty_programs", ["source"])
    for column, kind in (
        ("min_payout", sa.Float()),
        ("max_payout", sa.Float()),
    ):
        op.add_column("bounty_programs", sa.Column(column, kind, nullable=True))
    op.add_column(
        "bounty_programs",
        sa.Column("payout_currency", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "bounty_programs", sa.Column("safe_harbor", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "bounty_programs", sa.Column("requires_2fa", sa.Boolean(), nullable=True)
    )

    op.add_column(
        "instance_settings",
        sa.Column(
            "bounty_feed_interval",
            sa.String(length=16),
            nullable=False,
            server_default="six_hours",
        ),
    )
    op.add_column(
        "instance_settings",
        sa.Column("bounty_feed_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "bounty_feed_synced_at")
    op.drop_column("instance_settings", "bounty_feed_interval")
    op.drop_column("bounty_programs", "requires_2fa")
    op.drop_column("bounty_programs", "safe_harbor")
    op.drop_column("bounty_programs", "payout_currency")
    op.drop_column("bounty_programs", "max_payout")
    op.drop_column("bounty_programs", "min_payout")
    op.drop_index("ix_bounty_programs_source", table_name="bounty_programs")
    op.drop_column("bounty_programs", "source")
