"""AI services on web assets: http_assets.ai_* and subdomains.ai_services

Revision ID: 7b3e9d1c5a42
Revises: 1e7c4a9d2b58
Create Date: 2026-09-25
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "7b3e9d1c5a42"
down_revision: str | None = "1e7c4a9d2b58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "http_assets",
        sa.Column("ai_checked", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("http_assets", sa.Column("ai_service", sa.String(64), nullable=True))
    op.add_column("http_assets", sa.Column("ai_category", sa.String(32), nullable=True))
    op.add_column(
        "http_assets", sa.Column("ai_endpoint", sa.String(500), nullable=True)
    )
    op.add_column("http_assets", sa.Column("ai_models", sa.JSON(), nullable=True))
    op.add_column("subdomains", sa.Column("ai_services", sa.JSON(), nullable=True))
    op.execute(
        "CREATE INDEX ix_http_assets_ai_service ON http_assets (scan_id, ai_service) "
        "WHERE ai_service IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_http_assets_ai_models_gin ON http_assets "
        "USING gin ((ai_models::jsonb)) WHERE ai_models IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_subdomains_ai_services_gin ON subdomains "
        "USING gin ((ai_services::jsonb))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_subdomains_ai_services_gin")
    op.execute("DROP INDEX IF EXISTS ix_http_assets_ai_models_gin")
    op.execute("DROP INDEX IF EXISTS ix_http_assets_ai_service")
    op.drop_column("subdomains", "ai_services")
    for column in (
        "ai_models",
        "ai_endpoint",
        "ai_category",
        "ai_service",
        "ai_checked",
    ):
        op.drop_column("http_assets", column)
