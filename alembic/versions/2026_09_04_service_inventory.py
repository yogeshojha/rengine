"""service-level port inventory + per-address port-scan policy

Revision ID: a4c7e91b2d63
Revises: d17b3c9e5f24
Create Date: 2026-09-04 00:20:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a4c7e91b2d63"
down_revision: str | None = "d17b3c9e5f24"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ports",
        sa.Column(
            "service_class",
            sa.String(length=16),
            nullable=False,
            server_default="other",
        ),
    )
    op.add_column(
        "ports",
        sa.Column("is_http", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ports",
        sa.Column("tls", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("ports", sa.Column("product", sa.String(length=200), nullable=True))
    op.add_column("ports", sa.Column("version", sa.String(length=100), nullable=True))
    op.add_column("ports", sa.Column("banner", sa.String(length=1000), nullable=True))
    op.add_column(
        "ports",
        sa.Column(
            "cpe",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_index("ix_ports_service_class", "ports", ["service_class"])
    op.create_index("ix_ports_is_http", "ports", ["is_http"])
    op.create_index("ix_ports_service_name", "ports", ["service_name"])
    op.create_index("ix_ports_scan_ip", "ports", ["scan_id", "ip"])

    op.add_column(
        "ip_addresses", sa.Column("cdn_type", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "ip_addresses", sa.Column("scan_policy", sa.String(length=16), nullable=True)
    )
    op.add_column(
        "ip_addresses",
        sa.Column("scan_policy_reason", sa.String(length=32), nullable=True),
    )
    op.create_index("ix_ip_addresses_scan_policy", "ip_addresses", ["scan_policy"])


def downgrade() -> None:
    op.drop_index("ix_ip_addresses_scan_policy", table_name="ip_addresses")
    op.drop_column("ip_addresses", "scan_policy_reason")
    op.drop_column("ip_addresses", "scan_policy")
    op.drop_column("ip_addresses", "cdn_type")
    op.drop_index("ix_ports_scan_ip", table_name="ports")
    op.drop_index("ix_ports_service_name", table_name="ports")
    op.drop_index("ix_ports_is_http", table_name="ports")
    op.drop_index("ix_ports_service_class", table_name="ports")
    for col in (
        "cpe",
        "banner",
        "version",
        "product",
        "tls",
        "is_http",
        "service_class",
    ):
        op.drop_column("ports", col)
