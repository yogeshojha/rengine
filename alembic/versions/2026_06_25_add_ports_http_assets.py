"""add ports + http_assets tables and scans.http_assets_found

Revision ID: e7c9a1b3d5f8
Revises: d6b8f0a2c4e7
Create Date: 2026-06-25 14:00:00.000000+00:00

Expansion-phase assets: open Ports (naabu) and enriched HttpAssets (httpx + tlsx),
plus the http_assets headline rollup on scans.
"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "e7c9a1b3d5f8"
down_revision: str | None = "d6b8f0a2c4e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column(
            "http_assets_found", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    op.create_table(
        "ports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("ip", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column(
            "protocol",
            sqlmodel.sql.sqltypes.AutoString(length=8),
            nullable=False,
            server_default="tcp",
        ),
        sa.Column(
            "state",
            sqlmodel.sql.sqltypes.AutoString(length=16),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "service_name", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "source", sqlmodel.sql.sqltypes.AutoString(length=30), nullable=False
        ),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scan_id", "ip", "number", "protocol", name="uq_port_scan_ip_num_proto"
        ),
    )
    op.create_index(op.f("ix_ports_id"), "ports", ["id"], unique=False)
    op.create_index(op.f("ix_ports_scan_id"), "ports", ["scan_id"], unique=False)
    op.create_index(op.f("ix_ports_target_id"), "ports", ["target_id"], unique=False)
    op.create_index(op.f("ix_ports_project_id"), "ports", ["project_id"], unique=False)
    op.create_index(op.f("ix_ports_ip"), "ports", ["ip"], unique=False)
    op.create_index(op.f("ix_ports_number"), "ports", ["number"], unique=False)

    op.create_table(
        "http_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("url", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=False),
        sa.Column("host", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "scheme",
            sqlmodel.sql.sqltypes.AutoString(length=8),
            nullable=False,
            server_default="https",
        ),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column(
            "title", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True
        ),
        sa.Column(
            "webserver", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("content_length", sa.Integer(), nullable=True),
        sa.Column(
            "content_type", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column(
            "location", sqlmodel.sql.sqltypes.AutoString(length=2000), nullable=True
        ),
        sa.Column("tech", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("ip", sqlmodel.sql.sqltypes.AutoString(length=45), nullable=True),
        sa.Column("cname", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column("asn", sa.Integer(), nullable=True),
        sa.Column(
            "asn_org", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True
        ),
        sa.Column("is_cdn", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "cdn_name", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True
        ),
        sa.Column("waf", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("jarm", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column(
            "favicon_hash", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True
        ),
        sa.Column(
            "content_hash", sqlmodel.sql.sqltypes.AutoString(length=80), nullable=True
        ),
        sa.Column(
            "tls_issuer", sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True
        ),
        sa.Column(
            "tls_subject_cn",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("tls_sans", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("tls_not_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tls_self_signed", sa.Boolean(), nullable=True),
        sa.Column("tls_expired", sa.Boolean(), nullable=True),
        sa.Column(
            "tls_version", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True
        ),
        sa.Column(
            "screenshot_path",
            sqlmodel.sql.sqltypes.AutoString(length=500),
            nullable=True,
        ),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_id", "url", name="uq_httpasset_scan_url"),
    )
    op.create_index(op.f("ix_http_assets_id"), "http_assets", ["id"], unique=False)
    op.create_index(
        op.f("ix_http_assets_scan_id"), "http_assets", ["scan_id"], unique=False
    )
    op.create_index(
        op.f("ix_http_assets_target_id"), "http_assets", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_http_assets_project_id"), "http_assets", ["project_id"], unique=False
    )
    op.create_index(op.f("ix_http_assets_host"), "http_assets", ["host"], unique=False)
    op.create_index(
        op.f("ix_http_assets_status_code"),
        "http_assets",
        ["status_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_http_assets_is_cdn"), "http_assets", ["is_cdn"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_http_assets_is_cdn"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_status_code"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_host"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_project_id"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_target_id"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_scan_id"), table_name="http_assets")
    op.drop_index(op.f("ix_http_assets_id"), table_name="http_assets")
    op.drop_table("http_assets")

    op.drop_index(op.f("ix_ports_number"), table_name="ports")
    op.drop_index(op.f("ix_ports_ip"), table_name="ports")
    op.drop_index(op.f("ix_ports_project_id"), table_name="ports")
    op.drop_index(op.f("ix_ports_target_id"), table_name="ports")
    op.drop_index(op.f("ix_ports_scan_id"), table_name="ports")
    op.drop_index(op.f("ix_ports_id"), table_name="ports")
    op.drop_table("ports")

    op.drop_column("scans", "http_assets_found")
