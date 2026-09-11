"""a certificate is re-checked between scans, and the row says when

Revision ID: c19a5f3b7d84
Revises: b4c81e77a250
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c19a5f3b7d84"
down_revision: str | None = "b4c81e77a250"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("subdomains", sa.Column("tls_checked_at", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_subdomains_tls_recheck",
        "subdomains",
        ["tls_not_after", "tls_checked_at"],
        postgresql_where=sa.text("tls_not_after IS NOT NULL"),
    )
    op.add_column(
        "instance_settings",
        sa.Column(
            "cert_recheck_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("instance_settings", "cert_recheck_enabled")
    op.drop_index("ix_subdomains_tls_recheck", table_name="subdomains")
    op.drop_column("subdomains", "tls_checked_at")
