"""ai_connections: saved AI providers, one in use

Revision ID: 7d3c9e5b1a46
Revises: 4b8e1f2a7c90
Create Date: 2026-10-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7d3c9e5b1a46"
down_revision: str | None = "4b8e1f2a7c90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "ai_connections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("api_key_encrypted", sa.String(), nullable=True),
        sa.Column("base_url", sa.String(length=300), nullable=True),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("input_per_mtok", sa.Float(), nullable=True),
        sa.Column("output_per_mtok", sa.Float(), nullable=True),
        sa.Column("workspace_id", sa.String(length=80), nullable=True),
        sa.Column("last_test_at", _TZ, nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column("last_test_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", _TZ, nullable=False),
        sa.Column("updated_at", _TZ, nullable=False),
        sa.UniqueConstraint("name", name="uq_ai_connection_name"),
    )
    op.add_column(
        "instance_settings", sa.Column("ai_connection_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_instance_settings_ai_connection",
        "instance_settings",
        "ai_connections",
        ["ai_connection_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("instance_settings", "ai_provider")
    op.drop_column("instance_settings", "ai_model")
    op.drop_column("instance_settings", "ai_api_key_encrypted")


def downgrade() -> None:
    op.add_column(
        "instance_settings",
        sa.Column("ai_api_key_encrypted", sa.String(), nullable=True),
    )
    op.add_column(
        "instance_settings", sa.Column("ai_model", sa.String(), nullable=True)
    )
    op.add_column(
        "instance_settings", sa.Column("ai_provider", sa.String(), nullable=True)
    )
    op.drop_constraint(
        "fk_instance_settings_ai_connection", "instance_settings", type_="foreignkey"
    )
    op.drop_column("instance_settings", "ai_connection_id")
    op.drop_table("ai_connections")
