"""Encrypt scan engine headers and tool arguments at rest.

Revision ID: 3f8b2d6c1a94
Revises: c5e1f9a3b7d2
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.utils.crypto import encrypt_secret, try_decrypt

revision: str = "3f8b2d6c1a94"
down_revision: str | None = "c5e1f9a3b7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = ("global_headers", "tool_options")


def upgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            "scan_engines",
            column,
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using=f"{column}::text",
        )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, global_headers, tool_options FROM scan_engines")
    )
    for row_id, headers, options in rows.fetchall():
        bind.execute(
            sa.text(
                "UPDATE scan_engines SET global_headers = :headers, "
                "tool_options = :options WHERE id = :id"
            ),
            {
                "id": row_id,
                "headers": encrypt_secret(headers),
                "options": encrypt_secret(options),
            },
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, global_headers, tool_options FROM scan_engines")
    )
    for row_id, headers, options in rows.fetchall():
        bind.execute(
            sa.text(
                "UPDATE scan_engines SET global_headers = :headers, "
                "tool_options = :options WHERE id = :id"
            ),
            {
                "id": row_id,
                "headers": try_decrypt(headers) or "[]",
                "options": try_decrypt(options) or "{}",
            },
        )
    for column in _COLUMNS:
        op.alter_column(
            "scan_engines",
            column,
            type_=sa.JSON(),
            existing_nullable=False,
            postgresql_using=f"{column}::json",
        )
