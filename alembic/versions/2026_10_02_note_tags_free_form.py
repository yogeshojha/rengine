"""free-form note tags, triage reasons as notes

Revision ID: 4b8e1f2a7c90
Revises: f6c39a8d5e12
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision: str = "4b8e1f2a7c90"
down_revision: str | None = "f6c39a8d5e12"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRIGRAM = (("ix_notes_body_trgm", "body"), ("ix_notes_title_trgm", "title"))


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "tags", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")
        ),
    )
    op.create_index("ix_notes_tags", "notes", ["tags"], postgresql_using="gin")
    op.drop_index("ix_note_tags_tag_id", table_name="note_tags")
    op.drop_table("note_tags")

    op.add_column(
        "notes", sa.Column("triage_state", sa.String(length=20), nullable=True)
    )
    op.create_index(
        "ix_notes_triage",
        "notes",
        ["target_id", "asset_key", "triage_state", sa.text("created_at DESC")],
        postgresql_where=sa.text("triage_state IS NOT NULL"),
    )
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, column in _TRIGRAM:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON notes "
            f"USING gin ({column} gin_trgm_ops)"
        )
    op.drop_column("vulnerability_triage", "note")


def downgrade() -> None:
    op.add_column(
        "vulnerability_triage",
        sa.Column("note", sa.String(length=2000), nullable=True),
    )
    for name, _ in _TRIGRAM:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.drop_index("ix_notes_triage", table_name="notes")
    op.drop_column("notes", "triage_state")

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
    op.drop_index("ix_notes_tags", table_name="notes")
    op.drop_column("notes", "tags")
