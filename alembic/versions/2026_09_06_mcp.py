"""mcp: service tokens and the server switch on instance settings

Revision ID: a91d47c30fb2
Revises: f7c31a9d24b8
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a91d47c30fb2"
down_revision: str | None = "f7c31a9d24b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("capabilities", sa.JSON(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_client", sa.String(length=120), nullable=True),
        sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mcp_tokens_id", "mcp_tokens", ["id"])
    op.create_index("ix_mcp_tokens_name", "mcp_tokens", ["name"])
    op.create_index("ix_mcp_tokens_project_id", "mcp_tokens", ["project_id"])
    op.create_index(
        "ix_mcp_tokens_token_hash", "mcp_tokens", ["token_hash"], unique=True
    )

    op.add_column(
        "instance_settings",
        sa.Column(
            "mcp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "instance_settings",
        sa.Column("mcp_settings", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "mcp_settings")
    op.drop_column("instance_settings", "mcp_enabled")
    op.drop_index("ix_mcp_tokens_token_hash", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_project_id", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_name", table_name="mcp_tokens")
    op.drop_index("ix_mcp_tokens_id", table_name="mcp_tokens")
    op.drop_table("mcp_tokens")
