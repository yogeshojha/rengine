"""case-fold target values so one host is one target

Revision ID: d5a91c73e28f
Revises: c93e5a7f0b41
Create Date: 2026-09-13 00:10:00.000000+00:00

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d5a91c73e28f"
down_revision: str | None = "c93e5a7f0b41"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# a row whose folded value already exists in the project is left for the operator to merge
_FOLD = """
UPDATE targets AS t
SET target_value = lower(t.target_value)
WHERE t.target_value <> lower(t.target_value)
  AND t.target_type <> 'URL'
  AND NOT EXISTS (
      SELECT 1 FROM targets AS other
      WHERE other.project_id = t.project_id
        AND other.id <> t.id
        AND other.target_value = lower(t.target_value)
  )
"""


def upgrade() -> None:
    op.execute(_FOLD)


def downgrade() -> None:
    """Irreversible: the original casing of each folded value is not kept, and the
    folded rows are indistinguishable from targets entered in lower case.
    """
