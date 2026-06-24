"""target delete cascade: scans CASCADE, activity_logs SET NULL on target delete

Revision ID: c4f6a8e0b2d3
Revises: b2e4c6a8d0f1
Create Date: 2026-06-24 00:00:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4f6a8e0b2d3"
down_revision: str | None = "b2e4c6a8d0f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("scans_target_id_fkey", "scans", type_="foreignkey")
    op.create_foreign_key(
        "scans_target_id_fkey",
        "scans",
        "targets",
        ["target_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint(
        "activity_logs_target_id_fkey", "activity_logs", type_="foreignkey"
    )
    op.create_foreign_key(
        "activity_logs_target_id_fkey",
        "activity_logs",
        "targets",
        ["target_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "activity_logs_target_id_fkey", "activity_logs", type_="foreignkey"
    )
    op.create_foreign_key(
        "activity_logs_target_id_fkey",
        "activity_logs",
        "targets",
        ["target_id"],
        ["id"],
    )

    op.drop_constraint("scans_target_id_fkey", "scans", type_="foreignkey")
    op.create_foreign_key(
        "scans_target_id_fkey",
        "scans",
        "targets",
        ["target_id"],
        ["id"],
    )
