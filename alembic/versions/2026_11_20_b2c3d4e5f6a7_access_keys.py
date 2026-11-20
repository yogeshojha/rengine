"""access keys

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEVELS = ("read", "write")


def upgrade() -> None:
    postgresql.ENUM(*LEVELS, name="accesskeylevel").create(op.get_bind())
    op.create_table(
        "access_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=80), nullable=False),
        sa.Column("prefix", sa.VARCHAR(length=32), nullable=False),
        sa.Column("token_hash", sa.VARCHAR(length=64), nullable=False),
        sa.Column(
            "access",
            postgresql.ENUM(*LEVELS, name="accesskeylevel", create_type=False),
            nullable=False,
        ),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_used_ip", sa.VARCHAR(length=64), nullable=True),
        sa.Column("use_count", sa.INTEGER(), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="access_keys_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="access_keys_pkey"),
    )
    op.create_index("ix_access_keys_user_id", "access_keys", ["user_id"])
    op.create_index(
        "ix_access_keys_token_hash", "access_keys", ["token_hash"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ix_access_keys_token_hash", table_name="access_keys")
    op.drop_index("ix_access_keys_user_id", table_name="access_keys")
    op.drop_table("access_keys")
    postgresql.ENUM(name="accesskeylevel").drop(op.get_bind())
