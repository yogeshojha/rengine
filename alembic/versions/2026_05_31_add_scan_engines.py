"""add scan engines

Revision ID: a1b2c3d4e5f6
Revises: d55cda538e83
Create Date: 2026-05-31 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "4c5deccf464f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_engines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.Column("intensity", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("global_threads", sa.Integer(), nullable=False),
        sa.Column("global_http_crawl", sa.Boolean(), nullable=False),
        sa.Column("global_headers", sa.JSON(), nullable=False),
        sa.Column("discovery", sa.JSON(), nullable=False),
        sa.Column("expansion", sa.JSON(), nullable=False),
        sa.Column("depth", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_engines_id"), "scan_engines", ["id"], unique=False)
    op.create_index(
        op.f("ix_scan_engines_project_id"), "scan_engines", ["project_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_scan_engines_project_id"), table_name="scan_engines")
    op.drop_index(op.f("ix_scan_engines_id"), table_name="scan_engines")
    op.drop_table("scan_engines")
