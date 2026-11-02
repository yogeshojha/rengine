"""investigations and their plans

Revision ID: c1a2b3d4e5f6
Revises: b4f348070912
Create Date: 2026-11-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "c1a2b3d4e5f6"
down_revision: str | None = "b4f348070912"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("dimension", sa.VARCHAR(length=32), nullable=False),
        sa.Column("fingerprint", sa.VARCHAR(length=500), nullable=False),
        sa.Column("verdict", sa.VARCHAR(length=24), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("started_by", sa.UUID(), nullable=True),
        sa.Column("by_rule", sa.BOOLEAN(), nullable=False),
        sa.Column("requests_spent", sa.INTEGER(), nullable=False),
        sa.Column("verified_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("model", sa.VARCHAR(length=80), nullable=True),
        sa.Column("input_tokens", sa.INTEGER(), nullable=False),
        sa.Column("output_tokens", sa.INTEGER(), nullable=False),
        sa.Column("cost_usd", sa.Float(), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="investigations_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="investigations_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="investigations_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["started_by"],
            ["users.id"],
            name="investigations_started_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="investigations_pkey"),
        sa.UniqueConstraint(
            "target_id", "fingerprint", name="uq_investigation_finding"
        ),
    )
    op.create_index(
        "ix_investigations_project_id", "investigations", ["project_id"]
    )
    op.create_index("ix_investigations_target_id", "investigations", ["target_id"])
    op.create_index("ix_investigations_scan_id", "investigations", ["scan_id"])
    op.create_index(
        "ix_investigations_scan_verdict",
        "investigations",
        ["scan_id", "verdict"],
    )
    op.create_index(
        "ix_investigations_project_updated",
        "investigations",
        ["project_id", "updated_at"],
    )

    op.create_table(
        "investigation_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("investigation_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.VARCHAR(length=16), nullable=False),
        sa.Column("template_id", sa.VARCHAR(length=200), nullable=False),
        sa.Column("template_name", sa.VARCHAR(length=200), nullable=True),
        sa.Column("host", sa.VARCHAR(length=255), nullable=False),
        sa.Column("reason", sa.VARCHAR(length=280), nullable=True),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("refusal_reason", sa.VARCHAR(length=24), nullable=True),
        sa.Column("request_count", sa.INTEGER(), nullable=True),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("launched_scan_id", sa.UUID(), nullable=True),
        sa.Column("result", sa.VARCHAR(length=24), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["investigation_id"],
            ["investigations.id"],
            name="investigation_plans_investigation_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
            name="investigation_plans_approved_by_fkey",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["launched_scan_id"],
            ["scans.id"],
            name="investigation_plans_launched_scan_id_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="investigation_plans_pkey"),
    )
    op.create_index(
        "ix_investigation_plans_investigation_id",
        "investigation_plans",
        ["investigation_id"],
    )
    op.create_index(
        "ix_investigation_plans_inv_created",
        "investigation_plans",
        ["investigation_id", "created_at"],
    )
    op.create_index(
        "ix_investigation_plans_state", "investigation_plans", ["state"]
    )
    op.create_index(
        "ix_investigation_plans_launched",
        "investigation_plans",
        ["launched_scan_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_investigation_plans_launched", table_name="investigation_plans"
    )
    op.drop_index("ix_investigation_plans_state", table_name="investigation_plans")
    op.drop_index(
        "ix_investigation_plans_inv_created", table_name="investigation_plans"
    )
    op.drop_index(
        "ix_investigation_plans_investigation_id",
        table_name="investigation_plans",
    )
    op.drop_table("investigation_plans")
    op.drop_index(
        "ix_investigations_project_updated", table_name="investigations"
    )
    op.drop_index("ix_investigations_scan_verdict", table_name="investigations")
    op.drop_index("ix_investigations_scan_id", table_name="investigations")
    op.drop_index("ix_investigations_target_id", table_name="investigations")
    op.drop_index("ix_investigations_project_id", table_name="investigations")
    op.drop_table("investigations")
