"""lookalike domains per scan and their triage per target

Revision ID: 3c8e2b7f41a9
Revises: fe47e3eef6a7
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "3c8e2b7f41a9"
down_revision: str | None = "fe47e3eef6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "lookalike_domains",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("apex", sa.String(length=253), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("display", sa.String(length=253), nullable=False),
        sa.Column("technique", sa.String(length=32), nullable=False),
        sa.Column("verdict", sa.String(length=16), nullable=False),
        sa.Column("link_reason", sa.String(length=16), nullable=True),
        sa.Column("a", sa.JSON(), nullable=False),
        sa.Column("aaaa", sa.JSON(), nullable=False),
        sa.Column("mx", sa.JSON(), nullable=False),
        sa.Column("ns", sa.JSON(), nullable=False),
        sa.Column("parked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("final_url", sa.String(length=2000), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("similarity", sa.Integer(), nullable=True),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrar", sa.String(length=200), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "scan_id", "domain", name="uq_lookalike_domains_scan_domain"
        ),
    )
    for column in ("scan_id", "target_id", "project_id", "domain", "verdict"):
        op.create_index(f"ix_lookalike_domains_{column}", "lookalike_domains", [column])
    op.create_index(
        "ix_lookalike_domains_scan_discovered",
        "lookalike_domains",
        ["scan_id", "discovered_at"],
    )
    op.create_index(
        "ix_lookalike_domains_target_discovered",
        "lookalike_domains",
        ["target_id", "discovered_at"],
    )

    op.create_table(
        "lookalike_triage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "target_id", "domain", name="uq_lookalike_triage_target_domain"
        ),
    )
    op.create_index(
        "ix_lookalike_triage_project_id", "lookalike_triage", ["project_id"]
    )
    op.create_index("ix_lookalike_triage_target_id", "lookalike_triage", ["target_id"])


def downgrade() -> None:
    op.drop_table("lookalike_triage")
    op.drop_table("lookalike_domains")
