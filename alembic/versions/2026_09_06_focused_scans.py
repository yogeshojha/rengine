"""focused scans: scope + parent run on scans, and the asset_rechecks diff table

Revision ID: d1a4c8e07b93
Revises: c9d2a7f13e58
Create Date: 2026-09-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d1a4c8e07b93"
down_revision: str | None = "c9d2a7f13e58"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scans",
        sa.Column(
            "scope", sa.String(length=16), nullable=False, server_default="full"
        ),
    )
    op.add_column("scans", sa.Column("parent_scan_id", sa.Uuid(), nullable=True))
    op.create_index("ix_scans_scope", "scans", ["scope"])
    op.create_index("ix_scans_parent_scan_id", "scans", ["parent_scan_id"])
    op.create_foreign_key(
        "fk_scans_parent_scan_id",
        "scans",
        "scans",
        ["parent_scan_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_table(
        "asset_rechecks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("parent_scan_id", sa.Uuid(), nullable=False),
        sa.Column("dimension", sa.String(length=32), nullable=False),
        sa.Column("asset_kind", sa.String(length=16), nullable=False),
        sa.Column("asset_key", sa.String(length=500), nullable=False),
        sa.Column("changed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["target_id"], ["targets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_asset_rechecks_id", "asset_rechecks", ["id"])
    op.create_index("ix_asset_rechecks_project_id", "asset_rechecks", ["project_id"])
    op.create_index("ix_asset_rechecks_target_id", "asset_rechecks", ["target_id"])
    op.create_index("ix_asset_rechecks_scan_id", "asset_rechecks", ["scan_id"])
    op.create_index("ix_asset_rechecks_asset_key", "asset_rechecks", ["asset_key"])
    op.create_index(
        "ix_asset_rechecks_parent_lookup",
        "asset_rechecks",
        ["parent_scan_id", "asset_key"],
    )


def downgrade() -> None:
    op.drop_table("asset_rechecks")
    op.drop_constraint("fk_scans_parent_scan_id", "scans", type_="foreignkey")
    op.drop_index("ix_scans_parent_scan_id", table_name="scans")
    op.drop_index("ix_scans_scope", table_name="scans")
    op.drop_column("scans", "parent_scan_id")
    op.drop_column("scans", "scope")
