"""cloud storage buckets

Revision ID: a1c4e9f20b56
Revises: 5c9e1a7b3d42
Create Date: 2026-10-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "a1c4e9f20b56"
down_revision: str | None = "5c9e1a7b3d42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cloud_buckets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.VARCHAR(length=253), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=24), nullable=False),
        sa.Column("url", sa.VARCHAR(length=2000), nullable=False),
        sa.Column("source", sa.VARCHAR(length=16), nullable=False),
        sa.Column("access", sa.VARCHAR(length=16), nullable=False),
        sa.Column("region", sa.VARCHAR(length=32), nullable=True),
        sa.Column("object_count", sa.INTEGER(), nullable=True),
        sa.Column("size", sa.BIGINT(), nullable=True),
        sa.Column("first_seen", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("discovered_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["scan_id"],
            ["scans.id"],
            name="cloud_buckets_scan_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="cloud_buckets_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name="cloud_buckets_project_id_fkey"
        ),
        sa.PrimaryKeyConstraint("id", name="cloud_buckets_pkey"),
        sa.UniqueConstraint(
            "scan_id", "provider", "name", name="uq_cloud_buckets_scan_provider_name"
        ),
    )
    op.create_index("ix_cloud_buckets_scan_id", "cloud_buckets", ["scan_id"])
    op.create_index("ix_cloud_buckets_target_id", "cloud_buckets", ["target_id"])
    op.create_index("ix_cloud_buckets_project_id", "cloud_buckets", ["project_id"])
    op.create_index("ix_cloud_buckets_name", "cloud_buckets", ["name"])
    op.create_index("ix_cloud_buckets_access", "cloud_buckets", ["access"])

    op.create_table(
        "cloud_bucket_triage",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.VARCHAR(length=24), nullable=False),
        sa.Column("name", sa.VARCHAR(length=253), nullable=False),
        sa.Column("state", sa.VARCHAR(length=16), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="cloud_bucket_triage_project_id_fkey",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="cloud_bucket_triage_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="cloud_bucket_triage_pkey"),
        sa.UniqueConstraint(
            "target_id",
            "provider",
            "name",
            name="uq_cloud_bucket_triage_target_provider_name",
        ),
    )
    op.create_index(
        "ix_cloud_bucket_triage_project_id", "cloud_bucket_triage", ["project_id"]
    )
    op.create_index(
        "ix_cloud_bucket_triage_target_id", "cloud_bucket_triage", ["target_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cloud_bucket_triage_target_id", table_name="cloud_bucket_triage")
    op.drop_index("ix_cloud_bucket_triage_project_id", table_name="cloud_bucket_triage")
    op.drop_table("cloud_bucket_triage")
    op.drop_index("ix_cloud_buckets_access", table_name="cloud_buckets")
    op.drop_index("ix_cloud_buckets_name", table_name="cloud_buckets")
    op.drop_index("ix_cloud_buckets_project_id", table_name="cloud_buckets")
    op.drop_index("ix_cloud_buckets_target_id", table_name="cloud_buckets")
    op.drop_index("ix_cloud_buckets_scan_id", table_name="cloud_buckets")
    op.drop_table("cloud_buckets")
