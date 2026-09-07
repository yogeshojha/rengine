"""bounty_programs: keep the platform's own state and whether the hacker is a member

Revision ID: f7c3a5e18b92
Revises: e4b19d70c8a3
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f7c3a5e18b92"
down_revision: str | None = "e4b19d70c8a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bounty_programs", sa.Column("raw_state", sa.String(length=32), nullable=True)
    )
    op.add_column(
        "bounty_programs",
        sa.Column("joined", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "bounty_programs",
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bounty_programs_joined", "bounty_programs", ["joined"])


def downgrade() -> None:
    op.drop_index("ix_bounty_programs_joined", table_name="bounty_programs")
    op.drop_column("bounty_programs", "joined_at")
    op.drop_column("bounty_programs", "joined")
    op.drop_column("bounty_programs", "raw_state")
