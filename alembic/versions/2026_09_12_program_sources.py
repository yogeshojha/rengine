"""a program can be known from more than one source

Revision ID: c93e5a7f0b41
Revises: b7c2d81e4a96
Create Date: 2026-09-12 23:10:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "c93e5a7f0b41"
down_revision: str | None = "b7c2d81e4a96"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bounty_programs",
        sa.Column(
            "sources",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.execute("UPDATE bounty_programs SET sources = jsonb_build_array(source)")
    op.create_index(
        "ix_bounty_programs_sources",
        "bounty_programs",
        ["sources"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_bounty_programs_sources", table_name="bounty_programs")
    op.drop_column("bounty_programs", "sources")
