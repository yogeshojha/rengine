"""add http_assets.final_url (redirect destination)

Revision ID: f1a3c5e7d9b2
Revises: e7c9a1b3d5f8
Create Date: 2026-06-25 16:00:00.000000+00:00

Keeps `host`/`url` as the probed key (correlation) and records where a
followed redirect actually landed.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "f1a3c5e7d9b2"
down_revision: str | None = "e7c9a1b3d5f8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "http_assets",
        sa.Column(
            "final_url",
            sqlmodel.sql.sqltypes.AutoString(length=2000),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("http_assets", "final_url")
