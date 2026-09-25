"""subdomain names are stored lowercase

Revision ID: 8b3f61c0d2a7
Revises: c8e4f2a7d913
Create Date: 2026-09-24 17:00:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "8b3f61c0d2a7"
down_revision: str | None = "c8e4f2a7d913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE subdomains ADD CONSTRAINT ck_subdomains_name_lower "
        "CHECK (name = lower(name)) NOT VALID"
    )
    op.execute("ALTER TABLE subdomains VALIDATE CONSTRAINT ck_subdomains_name_lower")


def downgrade() -> None:
    op.execute("ALTER TABLE subdomains DROP CONSTRAINT ck_subdomains_name_lower")
