"""add onboarding

Revision ID: a7c1e9f2b3d4
Revises: d4e5f6a7b8c9
Create Date: 2026-06-20 00:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c1e9f2b3d4"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "instance_settings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "singleton_key", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False
        ),
        sa.Column(
            "instance_name",
            sqlmodel.sql.sqltypes.AutoString(length=120),
            nullable=False,
        ),
        sa.Column(
            "timezone", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False
        ),
        sa.Column("mode", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("onboarding_completed", sa.Boolean(), nullable=False),
        sa.Column("onboarding_completed_at", sa.DateTime(), nullable=True),
        sa.Column("onboarding_completed_by", sa.Uuid(), nullable=True),
        sa.Column("onboarding_step", sa.Integer(), nullable=False),
        sa.Column("onboarding_state", sa.JSON(), nullable=False),
        sa.Column("scan_history_retention_days", sa.Integer(), nullable=False),
        sa.Column("screenshot_retention_days", sa.Integer(), nullable=False),
        sa.Column("ai_enabled", sa.Boolean(), nullable=False),
        sa.Column("ai_provider", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("ai_model", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            "ai_api_key_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.Column("ai_features", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("singleton_key", name="uq_instance_settings_singleton"),
    )
    op.create_index(
        op.f("ix_instance_settings_id"), "instance_settings", ["id"], unique=False
    )

    op.create_table(
        "proxies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column("mode", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column(
            "endpoints_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("endpoint_count", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column(
            "last_test_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_proxies_id"), "proxies", ["id"], unique=False)

    op.create_table(
        "notification_channels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(length=120), nullable=False),
        sa.Column(
            "provider", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column(
            "config_encrypted", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_test_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True),
        sa.Column(
            "last_test_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_channels_id"),
        "notification_channels",
        ["id"],
        unique=False,
    )

    op.add_column(
        "users",
        sa.Column(
            "totp_secret_encrypted",
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "totp_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column("users", sa.Column("totp_backup_codes", sa.JSON(), nullable=True))

    op.add_column("api_keys", sa.Column("key_meta", sa.JSON(), nullable=True))

    op.add_column(
        "scan_contexts", sa.Column("proxy_id", sa.Uuid(), nullable=True)
    )
    op.create_index(
        op.f("ix_scan_contexts_proxy_id"),
        "scan_contexts",
        ["proxy_id"],
        unique=False,
    )

    op.add_column(
        "projects",
        sa.Column(
            "description", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
    )
    op.add_column(
        "projects",
        sa.Column(
            "label", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("projects", "label")
    op.drop_column("projects", "description")

    op.drop_index(op.f("ix_scan_contexts_proxy_id"), table_name="scan_contexts")
    op.drop_column("scan_contexts", "proxy_id")

    op.drop_column("api_keys", "key_meta")

    op.drop_column("users", "totp_backup_codes")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_encrypted")

    op.drop_index(
        op.f("ix_notification_channels_id"), table_name="notification_channels"
    )
    op.drop_table("notification_channels")

    op.drop_index(op.f("ix_proxies_id"), table_name="proxies")
    op.drop_table("proxies")

    op.drop_index(op.f("ix_instance_settings_id"), table_name="instance_settings")
    op.drop_table("instance_settings")
