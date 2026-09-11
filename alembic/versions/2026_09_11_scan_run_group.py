"""one focused run fans out into a scan per target, tied by run_group_id

Revision ID: a7f3c81d5e92
Revises: d27c6a90f1b3
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a7f3c81d5e92"
down_revision: str | None = "d27c6a90f1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans", sa.Column("run_group_id", UUID(as_uuid=True), nullable=True)
    )
    op.create_index("ix_scans_run_group_id", "scans", ["run_group_id"])


def downgrade() -> None:
    op.drop_index("ix_scans_run_group_id", table_name="scans")
    op.drop_column("scans", "run_group_id")
