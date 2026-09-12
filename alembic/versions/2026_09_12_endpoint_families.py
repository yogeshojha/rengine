"""endpoint families and per-rule drop counts

Revision ID: c4a7e21d8f03
Revises: e52a8c1d7b30
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.definitions.endpoints import family_for

revision: str = "c4a7e21d8f03"
down_revision: str | None = "e52a8c1d7b30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH = 5000


def _backfill() -> None:
    bind = op.get_bind()
    last = None
    while True:
        query = sa.text(
            "SELECT id, host, port, path, params::text AS params FROM endpoints "
            + ("WHERE id > :last " if last else "")
            + "ORDER BY id LIMIT :n"
        )
        rows = bind.execute(
            query, {"last": last, "n": _BATCH} if last else {"n": _BATCH}
        ).all()
        if not rows:
            return
        payload = []
        for row in rows:
            names = tuple(
                s.strip(' "')
                for s in (row.params or "[]").strip("[]").split(",")
                if s.strip(' "')
            )
            payload.append(
                {
                    "id": row.id,
                    "family": family_for(row.host, int(row.port), row.path, names),
                }
            )
        bind.execute(
            sa.text("UPDATE endpoints SET family = :family WHERE id = :id"), payload
        )
        last = rows[-1].id


def upgrade() -> None:
    op.add_column(
        "endpoints",
        sa.Column("family", sa.String(length=64), nullable=False, server_default=""),
    )
    _backfill()
    op.create_index("ix_endpoints_scan_family", "endpoints", ["scan_id", "family"])
    op.add_column(
        "endpoint_coverage",
        sa.Column("urls_dropped", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("endpoint_coverage", "urls_dropped")
    op.drop_index("ix_endpoints_scan_family", table_name="endpoints")
    op.drop_column("endpoints", "family")
