"""add ip_addresses table (IP-family discovery asset)

Revision ID: d6b8f0a2c4e7
Revises: c4f6a8e0b2d3
Create Date: 2026-06-25 12:00:00.000000+00:00

Per-scan IP asset produced by the Discovery phase for IP / IP_RANGE / ASN seeds:
seed/expansion provenance, reverse-DNS hostnames, and ASN/CDN enrichment.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "d6b8f0a2c4e7"
down_revision: str | None = "c4f6a8e0b2d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ip_addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("ip", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="4"),
        sa.Column(
            "source", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False
        ),
        sa.Column("ptr_hostnames", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("asn", sa.Integer(), nullable=True),
        sa.Column(
            "asn_org", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("prefix", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column(
            "country", sqlmodel.sql.sqltypes.AutoString(length=10), nullable=True
        ),
        sa.Column("is_cdn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "cdn_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column("is_alive", sa.Boolean(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "ip", name="uq_ipaddress_scan_ip"),
    )
    op.create_index(op.f("ix_ip_addresses_id"), "ip_addresses", ["id"], unique=False)
    op.create_index(
        op.f("ix_ip_addresses_scan_id"), "ip_addresses", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_ip_addresses_target_id"), "ip_addresses", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_ip_addresses_project_id"),
        "ip_addresses",
        ["project_id"],
        unique=False,
    )
    op.create_index(op.f("ix_ip_addresses_ip"), "ip_addresses", ["ip"], unique=False)
    op.create_index(op.f("ix_ip_addresses_asn"), "ip_addresses", ["asn"], unique=False)
    op.create_index(
        op.f("ix_ip_addresses_is_cdn"), "ip_addresses", ["is_cdn"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ip_addresses_is_cdn"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_asn"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_ip"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_project_id"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_target_id"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_scan_id"), table_name="ip_addresses")
    op.drop_index(op.f("ix_ip_addresses_id"), table_name="ip_addresses")
    op.drop_table("ip_addresses")
