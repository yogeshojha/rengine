"""drop scans.engine_id FK so engines stay deletable; scan keeps engine_name snapshot

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-31 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # engine_id mirrors context_id: an immutable historical snapshot, not a live
    # ref. Drop the FK so deleting a referenced engine no longer 500s; the scan
    # keeps engine_name. Keep an index for project/engine listing.
    op.drop_constraint("scans_engine_id_fkey", "scans", type_="foreignkey")
    op.create_index(op.f("ix_scans_engine_id"), "scans", ["engine_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_scans_engine_id"), table_name="scans")
    op.create_foreign_key(
        "scans_engine_id_fkey", "scans", "scan_engines", ["engine_id"], ["id"]
    )
