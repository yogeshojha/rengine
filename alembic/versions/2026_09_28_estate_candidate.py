"""passive dossier per candidate domain

Revision ID: c93a5f8e2d16
Revises: b7e4d19c6a02
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c93a5f8e2d16"
down_revision: str | None = "b7e4d19c6a02"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estate_candidate",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("resolves", sa.Boolean(), nullable=True),
        sa.Column("a", sa.JSON(), nullable=False),
        sa.Column("aaaa", sa.JSON(), nullable=False),
        sa.Column("cname", sa.String(length=253), nullable=True),
        sa.Column("ports", sa.JSON(), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrar", sa.String(length=200), nullable=True),
        sa.Column("takeover_provider", sa.String(length=64), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "project_id", "domain", name="uq_estate_candidate_project_domain"
        ),
    )
    op.create_index(
        "ix_estate_candidate_project_id", "estate_candidate", ["project_id"]
    )
    op.create_index("ix_estate_candidate_checked_at", "estate_candidate", ["checked_at"])


def downgrade() -> None:
    op.drop_index("ix_estate_candidate_checked_at", table_name="estate_candidate")
    op.drop_index("ix_estate_candidate_project_id", table_name="estate_candidate")
    op.drop_table("estate_candidate")
