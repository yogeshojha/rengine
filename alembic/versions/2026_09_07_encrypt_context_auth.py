"""Encrypt scan context credentials at rest."""

import json

import sqlalchemy as sa

from alembic import op
from shared.utils.crypto import try_decrypt

revision: str = "e8a1c5d29f47"
down_revision: str | None = "b7d2f4a91c63"
branch_labels = None
depends_on = None

_COLUMNS = ("auth", "extra_headers")


def upgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            "scan_contexts",
            column,
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using=f"{column}::text",
        )


def downgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, auth, extra_headers FROM scan_contexts"))
    for row_id, auth, headers in rows.fetchall():
        bind.execute(
            sa.text(
                "UPDATE scan_contexts SET auth = :auth, extra_headers = :headers "
                "WHERE id = :id"
            ),
            {"id": row_id, "auth": _decrypt(auth), "headers": _decrypt(headers)},
        )
    for column in _COLUMNS:
        op.alter_column(
            "scan_contexts",
            column,
            type_=sa.JSON(),
            existing_nullable=False,
            postgresql_using=f"{column}::json",
        )


def _decrypt(value: str | None) -> str:
    plain = try_decrypt(value) if value else None
    if plain is None:
        return value or "null"
    json.loads(plain)
    return plain
