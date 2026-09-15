"""secrets: values read out of stored responses

Revision ID: d2f8a6c31e97
Revises: c9e4f2a71b58
Create Date: 2026-09-14 18:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d2f8a6c31e97"
down_revision: str | None = "c9e4f2a71b58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "secrets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("group", sa.String(length=24), nullable=False),
        sa.Column("vendor", sa.String(length=60), nullable=False, server_default=""),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("is_secret", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("http_asset_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("sightings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("hosts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "scan_id", "fingerprint", name="uq_secret_scan_fingerprint"
        ),
    )
    for column in (
        "scan_id",
        "target_id",
        "project_id",
        "fingerprint",
        "kind",
        "group",
        "state",
        "subject",
        "host",
        "http_asset_id",
        "discovered_at",
    ):
        op.create_index(f"ix_secrets_{column}", "secrets", [column])
    op.create_index(
        "ix_secrets_scan_discovered", "secrets", ["scan_id", "discovered_at"]
    )
    op.create_index(
        "ix_secrets_target_discovered", "secrets", ["target_id", "discovered_at"]
    )
    op.create_index("ix_secrets_scan_state", "secrets", ["scan_id", "state"])
    op.create_index("ix_secrets_scan_kind", "secrets", ["scan_id", "kind"])

    op.create_table(
        "secret_sightings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("secret_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("host", sa.String(length=500), nullable=False),
        sa.Column("url", sa.String(length=2000), nullable=False),
        sa.Column("http_asset_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["secret_id"], ["secrets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint(
            "secret_id", "url", "source", name="uq_sighting_secret_url"
        ),
    )
    for column in ("secret_id", "scan_id", "target_id", "project_id", "http_asset_id"):
        op.create_index(f"ix_secret_sightings_{column}", "secret_sightings", [column])
    op.create_index(
        "ix_secret_sightings_scan_host", "secret_sightings", ["scan_id", "host"]
    )

    op.create_table(
        "secret_coverage",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("documents_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("documents_read", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bytes_read", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("truncated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detectors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("secrets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dropped", sa.JSON(), nullable=False),
        sa.Column("error", sa.String(length=2000), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.UniqueConstraint("scan_id", "source", name="uq_secret_coverage_scan_source"),
    )
    for column in ("scan_id", "target_id", "project_id"):
        op.create_index(f"ix_secret_coverage_{column}", "secret_coverage", [column])

    op.add_column(
        "scans",
        sa.Column("secrets_found", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("scans", "secrets_found")
    op.drop_table("secret_coverage")
    op.drop_table("secret_sightings")
    op.drop_table("secrets")
