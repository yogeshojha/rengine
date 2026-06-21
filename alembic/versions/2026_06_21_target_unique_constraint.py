"""add unique constraint on targets(target_value, project_id)

Revision ID: d1f4b6c8e0a2
Revises: c9e3a1b2d4f6
Create Date: 2026-06-21 00:10:00.000000+00:00

"""

from collections.abc import Sequence

from sqlalchemy import text

from alembic import op

revision: str = "d1f4b6c8e0a2"
down_revision: str | None = "c9e3a1b2d4f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    dupes = conn.execute(
        text(
            "SELECT target_value, project_id, COUNT(*) AS c FROM targets "
            "GROUP BY target_value, project_id HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if dupes:
        details = ", ".join(f"{d.target_value}({d.c})" for d in dupes)
        msg = (
            "Cannot add unique constraint: duplicate targets exist — "
            f"resolve these first: {details}"
        )
        raise RuntimeError(msg)
    op.create_unique_constraint(
        "uq_target_value_project", "targets", ["target_value", "project_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_target_value_project", "targets", type_="unique")
