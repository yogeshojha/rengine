"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

from collections.abc import Sequence

import sqlalchemy as sa  # noqa: F401 - most migrations use it; unused in an empty revision
import sqlmodel  # noqa: F401 - autogenerate renders sqlmodel column types

from alembic import op
% if imports:
${imports}
% endif

revision: str = ${repr(up_revision).replace("'", '"')}
down_revision: str | None = ${repr(down_revision).replace("'", '"')}
branch_labels: str | Sequence[str] | None = ${repr(branch_labels).replace("'", '"')}
depends_on: str | Sequence[str] | None = ${repr(depends_on).replace("'", '"')}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
