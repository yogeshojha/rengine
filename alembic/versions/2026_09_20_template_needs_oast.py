"""library: the checks that cannot run without an out-of-band server

Revision ID: d4a17b39ce62
Revises: c8f31a06e5b4
Create Date: 2026-09-20 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d4a17b39ce62"
down_revision: str | None = "c8f31a06e5b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "vuln_templates",
        sa.Column(
            "needs_oast", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.alter_column("vuln_templates", "needs_oast", server_default=None)


def downgrade() -> None:
    op.drop_column("vuln_templates", "needs_oast")
