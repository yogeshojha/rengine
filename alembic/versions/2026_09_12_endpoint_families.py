"""endpoint families and per-rule drop counts

Revision ID: c4a7e21d8f03
Revises: e52a8c1d7b30
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4a7e21d8f03"
down_revision: str | None = "e52a8c1d7b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "endpoints",
        sa.Column("family", sa.String(length=64), nullable=False, server_default=""),
    )
    op.create_index("ix_endpoints_scan_family", "endpoints", ["scan_id", "family"])
    op.add_column(
        "endpoint_coverage",
        sa.Column("urls_dropped", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("endpoint_coverage", "urls_dropped")
    op.drop_index("ix_endpoints_scan_family", table_name="endpoints")
    op.drop_column("endpoints", "family")
