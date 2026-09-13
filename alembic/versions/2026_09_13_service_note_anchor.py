"""service note anchors carry a bracketed IPv6 authority

Revision ID: e5c2f8b41d93
Revises: d3b8a1f70c42
Create Date: 2026-09-13 12:45:00.000000+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "e5c2f8b41d93"
down_revision: str | None = "d3b8a1f70c42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE notes
           SET asset_key = '[' || regexp_replace(asset_key, ':[0-9]+$', '')
                        || ']:' || regexp_replace(asset_key, '^.*:([0-9]+)$', '\\1')
         WHERE dimension = 'services'
           AND asset_key NOT LIKE '[%'
           AND asset_key ~ '^[0-9A-Fa-f:]+:[0-9]+$'
           AND asset_key ~ ':.*:.*:'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE notes
           SET asset_key = replace(replace(asset_key, '[', ''), ']', '')
         WHERE dimension = 'services' AND asset_key LIKE '[%'
        """
    )
