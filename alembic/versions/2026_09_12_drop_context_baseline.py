"""drop the unbuilt baseline fields from scan contexts

Revision ID: e4d92a15b7c3
Revises: c8b41f27d9a6
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e4d92a15b7c3"
down_revision: str | None = "c8b41f27d9a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("scan_contexts", "compare_baseline_scan_id")
    op.drop_column("scan_contexts", "scan_only_new_assets")


def downgrade() -> None:
    op.add_column(
        "scan_contexts",
        sa.Column("compare_baseline_scan_id", UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "scan_contexts",
        sa.Column(
            "scan_only_new_assets",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
