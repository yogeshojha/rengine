"""interest: rules, per-host signals, dismissals and the denormalised rank

Revision ID: b7d2f4a91c63
Revises: c4b8e1f70a92
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7d2f4a91c63"
down_revision: str | None = "c4b8e1f70a92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "interest_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=300), nullable=True),
        sa.Column("mode", sa.String(length=16), nullable=False),
        sa.Column("query", sa.String(length=2000), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("keyword_fields", sa.JSON(), nullable=False),
        sa.Column("live_only", sa.Boolean(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("builtin", sa.Boolean(), nullable=False),
        sa.Column("notify", sa.Boolean(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_interest_rules_id", "interest_rules", ["id"])
    op.create_index("ix_interest_rules_project_id", "interest_rules", ["project_id"])
    op.create_index("ix_interest_rules_enabled", "interest_rules", ["enabled"])
    op.create_index("ix_interest_rules_builtin", "interest_rules", ["builtin"])
    op.create_index(
        "ix_interest_rules_project_enabled", "interest_rules", ["project_id", "enabled"]
    )

    op.create_table(
        "interest_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subdomain_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("weight", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("reason", sa.String(length=400), nullable=False),
        sa.Column("evidence", sa.String(length=300), nullable=True),
        sa.Column("rule_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=True),
        sa.Column("prompt_version", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(
            ["subdomain_id"], ["subdomains.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scan_id", "subdomain_id", "source", "key", name="uq_interest_signal"
        ),
    )
    op.create_index("ix_interest_signals_id", "interest_signals", ["id"])
    op.create_index("ix_interest_signals_scan_id", "interest_signals", ["scan_id"])
    op.create_index("ix_interest_signals_target_id", "interest_signals", ["target_id"])
    op.create_index(
        "ix_interest_signals_project_id", "interest_signals", ["project_id"]
    )
    op.create_index(
        "ix_interest_signals_subdomain_id", "interest_signals", ["subdomain_id"]
    )
    op.create_index("ix_interest_signals_host", "interest_signals", ["host"])
    op.create_index("ix_interest_signals_source", "interest_signals", ["source"])
    op.create_index("ix_interest_signals_kind", "interest_signals", ["kind"])
    op.create_index("ix_interest_signals_rule_id", "interest_signals", ["rule_id"])
    op.create_index(
        "ix_interest_signals_scan_score", "interest_signals", ["scan_id", "weight"]
    )

    op.create_table(
        "interest_dismissals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("note", sa.String(length=300), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("target_id", "host", "kind", name="uq_interest_dismissal"),
    )
    op.create_index("ix_interest_dismissals_id", "interest_dismissals", ["id"])
    op.create_index(
        "ix_interest_dismissals_target_id", "interest_dismissals", ["target_id"]
    )
    op.create_index(
        "ix_interest_dismissals_project_id", "interest_dismissals", ["project_id"]
    )
    op.create_index("ix_interest_dismissals_host", "interest_dismissals", ["host"])

    op.add_column(
        "subdomains",
        sa.Column("interest_score", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "subdomains", sa.Column("interest_band", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "subdomains",
        sa.Column("interest_kinds", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_index("ix_subdomains_interest_score", "subdomains", ["interest_score"])
    op.create_index("ix_subdomains_interest_band", "subdomains", ["interest_band"])

    op.add_column(
        "scans", sa.Column("interest_signature", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "scans",
        sa.Column("interest_judged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scans", sa.Column("interest_model", sa.String(length=80), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("scans", "interest_model")
    op.drop_column("scans", "interest_judged_at")
    op.drop_column("scans", "interest_signature")
    op.drop_index("ix_subdomains_interest_band", table_name="subdomains")
    op.drop_index("ix_subdomains_interest_score", table_name="subdomains")
    op.drop_column("subdomains", "interest_kinds")
    op.drop_column("subdomains", "interest_band")
    op.drop_column("subdomains", "interest_score")
    op.drop_table("interest_dismissals")
    op.drop_table("interest_signals")
    op.drop_table("interest_rules")
