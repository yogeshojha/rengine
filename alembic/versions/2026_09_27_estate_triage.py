"""candidate target review state per project and domain

Revision ID: b7e4d19c6a02
Revises: 5d2e9a8c1b47
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7e4d19c6a02"
down_revision: str | None = "5d2e9a8c1b47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "estate_triage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "project_id", "domain", name="uq_estate_triage_project_domain"
        ),
    )
    op.create_index("ix_estate_triage_project_id", "estate_triage", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_estate_triage_project_id", table_name="estate_triage")
    op.drop_table("estate_triage")
