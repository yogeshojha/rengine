"""one connector per project and kind

Revision ID: f6c39a8d5e12
Revises: c3e8a1f47b92
Create Date: 2026-10-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f6c39a8d5e12"
down_revision: str | None = "c3e8a1f47b92"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "uq_connector_project_kind",
        "connectors",
        ["project_id", "kind"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_connector_project_kind", table_name="connectors")
