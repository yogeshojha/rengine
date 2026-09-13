"""web assets: the perceptual hash of a rendered page

Revision ID: d51c7a2e9f04
Revises: c3a9d1f45b82
Create Date: 2026-09-13 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d51c7a2e9f04"
down_revision: str | None = "c3a9d1f45b82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("http_assets", "subdomains")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table, sa.Column("screenshot_phash", sa.BigInteger(), nullable=True)
        )
        op.create_index(
            f"ix_{table}_screenshot_phash",
            table,
            ["scan_id", "screenshot_phash"],
            postgresql_where=sa.text("screenshot_phash IS NOT NULL"),
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_index(f"ix_{table}_screenshot_phash", table_name=table)
        op.drop_column(table, "screenshot_phash")
