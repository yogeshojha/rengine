"""software_cves.fixed_in: the nearest newer release in the scan without the CVE

Revision ID: 3c9e5a1f7d24
Revises: 2f7a9c4e1b60
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.utils.software import MAX_VERSION

revision: str = "3c9e5a1f7d24"
down_revision: str | None = "2f7a9c4e1b60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "software_cves",
        sa.Column("fixed_in", sa.String(length=MAX_VERSION), nullable=True),
    )
    op.add_column(
        "software_cves", sa.Column("fixed_in_assets", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("software_cves", "fixed_in_assets")
    op.drop_column("software_cves", "fixed_in")
