"""software on web assets is three-state, with an index on the rows still to evaluate

Revision ID: a3c9e1f52b7d
Revises: f7b3d9a24c81
Create Date: 2026-09-15 12:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a3c9e1f52b7d"
down_revision: str | None = "f7b3d9a24c81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PENDING_INDEX = "ix_http_assets_software_pending"
_AUTOVACUUM = (
    "autovacuum_analyze_scale_factor = 0.02, autovacuum_vacuum_scale_factor = 0.05"
)


def upgrade() -> None:
    op.alter_column(
        "http_assets",
        "software",
        existing_type=sa.JSON(),
        nullable=True,
        server_default=None,
    )
    op.execute(
        "UPDATE http_assets SET software = NULL WHERE json_array_length(software) = 0"
    )
    op.execute(f"ALTER TABLE software_cves SET ({_AUTOVACUUM})")
    with op.get_context().autocommit_block():
        op.execute(
            f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {_PENDING_INDEX} "
            "ON http_assets (scan_id) WHERE software IS NULL"
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_PENDING_INDEX}")
    op.execute(
        "ALTER TABLE software_cves RESET "
        "(autovacuum_analyze_scale_factor, autovacuum_vacuum_scale_factor)"
    )
    op.execute("UPDATE http_assets SET software = '[]' WHERE software IS NULL")
    op.alter_column(
        "http_assets",
        "software",
        existing_type=sa.JSON(),
        nullable=False,
        server_default="[]",
    )
