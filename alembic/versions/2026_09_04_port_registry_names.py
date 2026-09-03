"""name the ports an earlier scan left blank, from the IANA registry

Revision ID: b8f3d02a5c17
Revises: a4c7e91b2d63
Create Date: 2026-09-04 03:10:00.000000+00:00

service_for_port only learned the IANA tail after those rows were written. Backfilling
keeps the stored column and the UI in step: a name the row displays must also be a name
`service:<name>` can find, or the search counts stop being a promise.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.definitions.ports import ServiceClass, service_class, service_for_port

revision: str = "b8f3d02a5c17"
down_revision: str | None = "a4c7e91b2d63"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    numbers = (
        connection.execute(
            sa.text("SELECT DISTINCT number FROM ports WHERE service_name IS NULL")
        )
        .scalars()
        .all()
    )
    statement = sa.text(
        "UPDATE ports SET service_name = :name, "
        "service_class = CASE WHEN service_class = :other AND is_http IS FALSE "
        "THEN :klass ELSE service_class END "
        "WHERE number = :number AND service_name IS NULL"
    )
    for number in numbers:
        name = service_for_port(int(number))
        if not name:
            continue
        connection.execute(
            statement,
            {
                "name": name,
                "klass": service_class(name, int(number)),
                "other": ServiceClass.OTHER.value,
                "number": int(number),
            },
        )


def downgrade() -> None:
    pass
