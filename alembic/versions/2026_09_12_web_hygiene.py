"""hygiene checks on http assets and hosts

Revision ID: a81c3e5f9d27
Revises: a7c3e91f2b48
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a81c3e5f9d27"
down_revision: str | None = "a7c3e91f2b48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("http_assets", "subdomains")
_COLUMNS = ("hygiene_issues", "hygiene_checked")
_INDEX = "ix_subdomains_hygiene_gin"


def upgrade() -> None:
    for table in _TABLES:
        for column in _COLUMNS:
            op.add_column(table, sa.Column(column, sa.JSON(), nullable=True))
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_INDEX} "
            "ON subdomains USING gin ((hygiene_issues::jsonb))"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_INDEX}")
    for table in _TABLES:
        for column in _COLUMNS:
            op.drop_column(table, column)
