"""bounty reports, awards and account: the researcher's own record on a platform

Revision ID: e3b81c5f27a4
Revises: d4a17b39ce62
Create Date: 2026-09-24 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e3b81c5f27a4"
down_revision: str | None = "d4a17b39ce62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bounty_reports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("program_handle", sa.String(200), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("severity_score", sa.Float(), nullable=True),
        sa.Column("weakness", sa.String(200), nullable=True),
        sa.Column("asset_type", sa.String(48), nullable=True),
        sa.Column("asset_identifier", sa.String(1000), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("triaged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bounty_awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disclosed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "last_program_activity_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "platform", "external_id", name="uq_bounty_report_external"
        ),
    )
    op.create_index("ix_bounty_reports_platform", "bounty_reports", ["platform"])
    op.create_index(
        "ix_bounty_reports_program_handle", "bounty_reports", ["program_handle"]
    )
    op.create_index("ix_bounty_reports_state", "bounty_reports", ["state"])
    op.create_index("ix_bounty_reports_severity", "bounty_reports", ["severity"])
    op.create_index(
        "ix_bounty_reports_submitted_at", "bounty_reports", ["submitted_at"]
    )

    op.create_table(
        "bounty_awards",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("platform", sa.String(32), nullable=False),
        sa.Column("external_id", sa.String(100), nullable=False),
        sa.Column("report_external_id", sa.String(100), nullable=True),
        sa.Column("program_handle", sa.String(200), nullable=True),
        sa.Column("program_name", sa.String(300), nullable=True),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("bonus", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("platform", "external_id", name="uq_bounty_award_external"),
    )
    op.create_index("ix_bounty_awards_platform", "bounty_awards", ["platform"])
    op.create_index(
        "ix_bounty_awards_report_external_id", "bounty_awards", ["report_external_id"]
    )
    op.create_index(
        "ix_bounty_awards_program_handle", "bounty_awards", ["program_handle"]
    )
    op.create_index("ix_bounty_awards_awarded_at", "bounty_awards", ["awarded_at"])

    op.create_table(
        "bounty_accounts",
        sa.Column("platform", sa.String(32), primary_key=True),
        sa.Column("username", sa.String(200), nullable=True),
        sa.Column("reputation", sa.Integer(), nullable=True),
        sa.Column("signal", sa.Float(), nullable=True),
        sa.Column("impact", sa.Float(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("bounty_accounts")
    op.drop_table("bounty_awards")
    op.drop_table("bounty_reports")
