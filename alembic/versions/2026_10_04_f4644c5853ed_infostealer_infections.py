"""infostealer infections

Revision ID: f4644c5853ed
Revises: cb7bd70d3f2e
Create Date: 2026-10-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "f4644c5853ed"
down_revision: str | None = "cb7bd70d3f2e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENTS = (
    "TARGET_ENRICHMENT_INFOSTEALER_COMPLETED",
    "TARGET_ENRICHMENT_INFOSTEALER_FAILED",
)


def upgrade() -> None:
    for event in EVENTS:
        op.execute(f"ALTER TYPE activityevent ADD VALUE IF NOT EXISTS '{event}'")

    op.add_column(
        "targets",
        sa.Column(
            "infostealer_status",
            postgresql.ENUM(name="taskstatus", create_type=False),
            server_default="SKIPPED",
            nullable=False,
        ),
    )
    op.alter_column("targets", "infostealer_status", server_default=None)
    op.add_column(
        "targets",
        sa.Column("infostealer_error", sa.VARCHAR(length=1000), nullable=True),
    )
    op.create_index("ix_targets_infostealer_status", "targets", ["infostealer_status"])

    op.add_column(
        "instance_settings",
        sa.Column(
            "infostealer_lookups",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )

    op.create_table(
        "target_infostealers",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("domain", sa.VARCHAR(length=253), nullable=False),
        sa.Column("checked_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("total", sa.INTEGER(), nullable=False),
        sa.Column("employees", sa.INTEGER(), nullable=False),
        sa.Column("users", sa.INTEGER(), nullable=False),
        sa.Column("third_parties", sa.INTEGER(), nullable=False),
        sa.Column("total_urls", sa.INTEGER(), nullable=False),
        sa.Column(
            "last_employee_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("last_user_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("families", sa.JSON(), nullable=False),
        sa.Column("passwords", sa.JSON(), nullable=False),
        sa.Column("applications", sa.JSON(), nullable=False),
        sa.Column("services", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="target_infostealers_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="target_infostealers_pkey"),
    )
    op.create_index(
        "ix_target_infostealers_target_id",
        "target_infostealers",
        ["target_id"],
        unique=True,
    )

    op.create_table(
        "infostealer_logins",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("audience", sa.VARCHAR(length=16), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("scheme", sa.VARCHAR(length=16), nullable=True),
        sa.Column("port", sa.INTEGER(), nullable=True),
        sa.Column("path", sa.VARCHAR(length=400), nullable=True),
        sa.Column("credentials", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="infostealer_logins_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="infostealer_logins_pkey"),
    )
    op.create_index(
        "ix_infostealer_logins_target_host",
        "infostealer_logins",
        ["target_id", "host"],
    )


def downgrade() -> None:
    op.drop_index("ix_infostealer_logins_target_host", table_name="infostealer_logins")
    op.drop_table("infostealer_logins")
    op.drop_index("ix_target_infostealers_target_id", table_name="target_infostealers")
    op.drop_table("target_infostealers")
    op.drop_column("instance_settings", "infostealer_lookups")
    op.drop_index("ix_targets_infostealer_status", table_name="targets")
    op.drop_column("targets", "infostealer_error")
    op.drop_column("targets", "infostealer_status")
