"""wordlists: the library a guessing stage reads from

Revision ID: e2b5d9f1a047
Revises: d1a4c8e07b93
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e2b5d9f1a047"
down_revision: str | None = "d1a4c8e07b93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wordlists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("filename", sa.String(length=200), nullable=False),
        sa.Column("words", sa.Integer(), nullable=False),
        sa.Column("bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wordlists_id", "wordlists", ["id"])
    op.create_index("ix_wordlists_slug", "wordlists", ["slug"], unique=True)
    op.create_index("ix_wordlists_origin", "wordlists", ["origin"])
    op.create_index("ix_wordlists_kind", "wordlists", ["kind"])


def downgrade() -> None:
    op.drop_index("ix_wordlists_kind", table_name="wordlists")
    op.drop_index("ix_wordlists_origin", table_name="wordlists")
    op.drop_index("ix_wordlists_slug", table_name="wordlists")
    op.drop_index("ix_wordlists_id", table_name="wordlists")
    op.drop_table("wordlists")
