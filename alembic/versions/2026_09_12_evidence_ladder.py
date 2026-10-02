"""evidence ladder on findings and software CVEs

Revision ID: b93d4e17c5a2
Revises: a81c3e5f9d27
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b93d4e17c5a2"
down_revision: str | None = "a81c3e5f9d27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (("software_cves", "inferred"), ("vulnerabilities", "observed"))


def upgrade() -> None:
    for table, default in _COLUMNS:
        op.add_column(
            table,
            sa.Column(
                "evidence",
                sa.String(length=16),
                nullable=False,
                server_default=default,
            ),
        )
        op.create_index(f"ix_{table}_evidence", table, ["evidence"])


def downgrade() -> None:
    for table, _default in _COLUMNS:
        op.drop_index(f"ix_{table}_evidence", table_name=table)
        op.drop_column(table, "evidence")
