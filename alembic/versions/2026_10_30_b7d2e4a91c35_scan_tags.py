"""scan tags

Revision ID: b7d2e4a91c35
Revises: a1c4e9f20b56
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b7d2e4a91c35"
down_revision: str | None = "a1c4e9f20b56"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scan_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=50), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="scan_tags_project_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="scan_tags_created_by_fkey",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="scan_tags_pkey"),
        sa.UniqueConstraint("project_id", "name", name="uq_scan_tags_project_name"),
    )
    op.create_index("ix_scan_tags_project_id", "scan_tags", ["project_id"])
    op.create_table(
        "scan_tag_links",
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="scan_tag_links_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["scan_tags.id"],
            name="scan_tag_links_tag_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("scan_id", "tag_id", name="scan_tag_links_pkey"),
    )
    op.create_index("ix_scan_tag_links_tag_id", "scan_tag_links", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_scan_tag_links_tag_id", table_name="scan_tag_links")
    op.drop_table("scan_tag_links")
    op.drop_index("ix_scan_tags_project_id", table_name="scan_tags")
    op.drop_table("scan_tags")
