"""encrypt api_keys.key_value at rest (Fernet)

Revision ID: c9e3a1b2d4f6
Revises: b8d2f0a1c4e5
Create Date: 2026-06-21 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op
from shared.utils.crypto import decrypt_secret, encrypt_secret, try_decrypt

revision: str = "c9e3a1b2d4f6"
down_revision: str | None = "b8d2f0a1c4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "api_keys",
        "key_value",
        type_=sa.String(length=1000),
        existing_type=sa.String(length=500),
        existing_nullable=False,
    )
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, key_value FROM api_keys")).fetchall()
    for row in rows:
        # idempotent: skip rows that already decrypt cleanly
        if try_decrypt(row.key_value) is not None:
            continue
        conn.execute(
            text("UPDATE api_keys SET key_value = :v WHERE id = :id"),
            {"v": encrypt_secret(row.key_value), "id": row.id},
        )


def downgrade() -> None:
    conn = op.get_bind()
    rows = conn.execute(text("SELECT id, key_value FROM api_keys")).fetchall()
    for row in rows:
        try:
            plain = decrypt_secret(row.key_value)
        except ValueError:
            continue
        conn.execute(
            text("UPDATE api_keys SET key_value = :v WHERE id = :id"),
            {"v": plain, "id": row.id},
        )
    op.alter_column(
        "api_keys",
        "key_value",
        type_=sa.String(length=500),
        existing_type=sa.String(length=1000),
        existing_nullable=False,
    )
