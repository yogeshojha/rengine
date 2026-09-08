"""connector notices are delivered to the proxy once, like actions

Revision ID: c3f7a1e05d92
Revises: a5d19c7e4b83
Create Date: 2026-09-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3f7a1e05d92"
down_revision: str | None = "a5d19c7e4b83"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "connector_candidates",
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_connector_candidates_notified_at", "connector_candidates", ["notified_at"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_connector_candidates_notified_at", table_name="connector_candidates"
    )
    op.drop_column("connector_candidates", "notified_at")
