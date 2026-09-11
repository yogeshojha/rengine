"""recon notes anchored to a durable asset identity, tagged from the project vocabulary

Revision ID: c8b41f27d9a6
Revises: a7f3c81d5e92
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "c8b41f27d9a6"
down_revision: str | None = "a7f3c81d5e92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("targets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "scan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("dimension", sa.String(length=32), nullable=True),
        sa.Column("asset_key", sa.String(length=500), nullable=True),
        sa.Column("asset_label", sa.String(length=500), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.String(length=20000), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="open"
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notes_project_id", "notes", ["project_id"])
    op.create_index("ix_notes_target_id", "notes", ["target_id"])
    op.create_index("ix_notes_scan_id", "notes", ["scan_id"])
    op.create_index("ix_notes_status", "notes", ["status"])
    op.create_index("ix_notes_created_at", "notes", ["created_at"])
    op.create_index("ix_notes_anchor", "notes", ["dimension", "asset_key"])

    op.create_table(
        "note_tags",
        sa.Column(
            "note_id",
            UUID(as_uuid=True),
            sa.ForeignKey("notes.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index("ix_note_tags_tag_id", "note_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_note_tags_tag_id", table_name="note_tags")
    op.drop_table("note_tags")
    for name in (
        "ix_notes_anchor",
        "ix_notes_created_at",
        "ix_notes_status",
        "ix_notes_scan_id",
        "ix_notes_target_id",
        "ix_notes_project_id",
    ):
        op.drop_index(name, table_name="notes")
    op.drop_table("notes")
