"""drop the engine settings no stage read

Revision ID: f2a7c93e1b48
Revises: a18f3c7d5e92
Create Date: 2026-09-13 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a7c93e1b48"
down_revision: str | None = "a18f3c7d5e92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_column("scan_engines", "global_threads")
    op.drop_column("scan_engines", "global_http_crawl")


def downgrade() -> None:
    op.add_column(
        "scan_engines",
        sa.Column(
            "global_http_crawl", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "scan_engines",
        sa.Column("global_threads", sa.Integer(), nullable=False, server_default="30"),
    )
