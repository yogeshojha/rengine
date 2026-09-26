"""version_key clamps a wide numeric run, so the NVD corpus is rebuilt once

Revision ID: d3b8a1f70c42
Revises: c7e41d9a2f60
Create Date: 2026-09-13 12:30:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d3b8a1f70c42"
down_revision: str | None = "c7e41d9a2f60"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("UPDATE threat_feeds SET version = NULL WHERE kind = 'nvd'")


def downgrade() -> None:
    """Nothing to restore: a cleared version only makes the next NVD sync rebuild
    the corpus, which it does under either schema.
    """
