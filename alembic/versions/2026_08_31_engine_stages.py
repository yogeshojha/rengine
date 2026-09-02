"""scan engines: three phase buckets -> one per-stage config map

Revision ID: d1a4c7e02b95
Revises: c7e9f1b3d5a8
Create Date: 2026-08-31 10:40:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d1a4c7e02b95"
down_revision: str | None = "c7e9f1b3d5a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_COLUMNS = ("discovery", "expansion", "depth")


def upgrade() -> None:
    op.add_column(
        "scan_engines",
        sa.Column(
            "stages",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )
    for column in _OLD_COLUMNS:
        op.drop_column("scan_engines", column)


def downgrade() -> None:
    for column in _OLD_COLUMNS:
        op.add_column(
            "scan_engines",
            sa.Column(
                column,
                postgresql.JSON(astext_type=sa.Text()),
                nullable=False,
                server_default="{}",
            ),
        )
    op.drop_column("scan_engines", "stages")
