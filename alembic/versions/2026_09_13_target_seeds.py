"""targets: assets stored against a target and folded into its scans

Revision ID: c3a9d1f45b82
Revises: b7f41e0c9d26
Create Date: 2026-09-13 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3a9d1f45b82"
down_revision: str | None = "b7f41e0c9d26"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "targets",
        sa.Column("seed_scans", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.create_table(
        "target_seeds",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("value", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("target_id", "value", name="uq_target_seed_value"),
    )
    op.create_index("ix_target_seeds_target_id", "target_seeds", ["target_id"])
    op.create_index("ix_target_seeds_project_id", "target_seeds", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_target_seeds_project_id", table_name="target_seeds")
    op.drop_index("ix_target_seeds_target_id", table_name="target_seeds")
    op.drop_table("target_seeds")
    op.drop_column("targets", "seed_scans")
