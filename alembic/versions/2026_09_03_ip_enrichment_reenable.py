"""clear the stale ip_enrichment:false saved when the stage was IP-targets-only

Revision ID: d17b3c9e5f24
Revises: c84f2a6b1d93
Create Date: 2026-09-03 12:30:00.000000+00:00

ip_enrichment used to be applies_to=IP_TARGETS, so on a domain engine the toggle
was inert and "off" recorded no opinion about ASN/country enrichment. Dropping the
key lets those engines fall back to the stage default; an explicit true is kept.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d17b3c9e5f24"
down_revision: str | None = "c84f2a6b1d93"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE scan_engines
        SET stages = cast(cast(stages AS jsonb) - 'ip_enrichment' AS json)
        WHERE cast(stages AS jsonb) -> 'ip_enrichment' ->> 'enabled' = 'false'
        """
    )


def downgrade() -> None:
    pass
