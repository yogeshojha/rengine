"""drop investigation indexes covered by a composite index or constraint

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
Create Date: 2026-11-08
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e3c4d5f6a7b8"
down_revision: str | None = "d2b3c4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_investigations_project_id", table_name="investigations")
    op.drop_index("ix_investigations_target_id", table_name="investigations")
    op.drop_index("ix_investigations_scan_id", table_name="investigations")
    op.drop_index(
        "ix_investigation_plans_investigation_id",
        table_name="investigation_plans",
    )


def downgrade() -> None:
    op.create_index(
        "ix_investigation_plans_investigation_id",
        "investigation_plans",
        ["investigation_id"],
    )
    op.create_index("ix_investigations_scan_id", "investigations", ["scan_id"])
    op.create_index("ix_investigations_target_id", "investigations", ["target_id"])
    op.create_index("ix_investigations_project_id", "investigations", ["project_id"])
