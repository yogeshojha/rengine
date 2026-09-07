"""bounty programs and their structured scopes

Revision ID: d17a83c6e2b4
Revises: c93b12f4a8d5
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d17a83c6e2b4"
down_revision: str | None = "c93b12f4a8d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bounty_programs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("handle", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=True),
        sa.Column("profile_picture", sa.String(length=1000), nullable=True),
        sa.Column("program_state", sa.String(length=16), nullable=False),
        sa.Column("submission_state", sa.String(length=16), nullable=False),
        sa.Column("offers_bounties", sa.Boolean(), nullable=False),
        sa.Column("open_scope", sa.Boolean(), nullable=True),
        sa.Column("gold_standard_safe_harbor", sa.Boolean(), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("started_accepting_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bookmarked", sa.Boolean(), nullable=False),
        sa.Column("reports_for_user", sa.Integer(), nullable=True),
        sa.Column("earnings_for_user", sa.Float(), nullable=True),
        sa.Column("scopes_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform", "handle", name="uq_bounty_program_handle"),
    )
    op.create_index("ix_bounty_programs_id", "bounty_programs", ["id"])
    op.create_index("ix_bounty_programs_platform", "bounty_programs", ["platform"])
    op.create_index("ix_bounty_programs_handle", "bounty_programs", ["handle"])
    op.create_index(
        "ix_bounty_programs_program_state", "bounty_programs", ["program_state"]
    )
    op.create_index(
        "ix_bounty_programs_submission_state", "bounty_programs", ["submission_state"]
    )
    op.create_index(
        "ix_bounty_programs_offers_bounties", "bounty_programs", ["offers_bounties"]
    )
    op.create_index("ix_bounty_programs_bookmarked", "bounty_programs", ["bookmarked"])
    op.create_index(
        "ix_bounty_programs_started_accepting_at",
        "bounty_programs",
        ["started_accepting_at"],
    )
    op.create_index("ix_bounty_programs_synced_at", "bounty_programs", ["synced_at"])

    op.create_table(
        "bounty_scopes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=48), nullable=False),
        sa.Column("asset_identifier", sa.String(length=1000), nullable=False),
        sa.Column("scope_state", sa.String(length=16), nullable=False),
        sa.Column("eligible_for_bounty", sa.Boolean(), nullable=True),
        sa.Column("max_severity", sa.String(length=16), nullable=True),
        sa.Column("instruction", sa.Text(), nullable=True),
        sa.Column("reference", sa.String(length=500), nullable=True),
        sa.Column("target_value", sa.String(length=500), nullable=True),
        sa.Column(
            "target_type",
            postgresql.ENUM(name="targettype", create_type=False),
            nullable=True,
        ),
        sa.Column("raw", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"], ["bounty_programs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "program_id", "asset_type", "asset_identifier", name="uq_bounty_scope_asset"
        ),
    )
    op.create_index("ix_bounty_scopes_id", "bounty_scopes", ["id"])
    op.create_index("ix_bounty_scopes_program_id", "bounty_scopes", ["program_id"])
    op.create_index("ix_bounty_scopes_asset_type", "bounty_scopes", ["asset_type"])
    op.create_index("ix_bounty_scopes_scope_state", "bounty_scopes", ["scope_state"])
    op.create_index("ix_bounty_scopes_target_value", "bounty_scopes", ["target_value"])


def downgrade() -> None:
    op.drop_table("bounty_scopes")
    op.drop_table("bounty_programs")
