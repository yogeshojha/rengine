"""http_assets.tracking_ids: analytics and ads accounts a page loads

Revision ID: 1e7c4a9d2b58
Revises: 8d2b6f0a4c13
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "1e7c4a9d2b58"
down_revision: str | None = "8d2b6f0a4c13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("http_assets", sa.Column("tracking_ids", sa.JSON(), nullable=True))
    op.execute(
        "CREATE INDEX ix_http_assets_tracking_gin ON http_assets "
        "USING gin ((tracking_ids::jsonb))"
    )
    op.execute("UPDATE http_assets SET hygiene_checked = NULL")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_http_assets_tracking_gin")
    op.drop_column("http_assets", "tracking_ids")
