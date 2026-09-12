"""connector inventory: endpoint shapes, no scan triggers, no sessions

Revision ID: e52a8c1d7b30
Revises: b93d4e17c5a2
Create Date: 2026-09-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.definitions.endpoints import shape_for

revision: str = "e52a8c1d7b30"
down_revision: str | None = "b93d4e17c5a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BATCH = 5000


def _backfill_shapes() -> None:
    conn = op.get_bind()
    last: str | None = None
    while True:
        query = sa.text(
            "SELECT id, path FROM endpoints"  # noqa: S608
            + (" WHERE id > :last" if last else "")
            + " ORDER BY id LIMIT :n"
        )
        params = {"n": _BATCH, **({"last": last} if last else {})}
        rows = conn.execute(query, params).fetchall()
        if not rows:
            return
        conn.execute(
            sa.text("UPDATE endpoints SET shape = :shape WHERE id = :id"),
            [{"id": row.id, "shape": shape_for(row.path)[0]} for row in rows],
        )
        last = str(rows[-1].id)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("connector_sessions"):
        op.drop_table("connector_sessions")
    present = {c["name"] for c in inspector.get_columns("connectors")}
    for column in (
        "import_mode",
        "target_id",
        "sync_trigger",
        "quiet_minutes",
        "queue_threshold",
        "capture_sessions",
    ):
        if column in present:
            op.drop_column("connectors", column)

    op.add_column(
        "endpoints",
        sa.Column("shape", sa.String(length=1500), nullable=False, server_default=""),
    )
    _backfill_shapes()
    op.create_index(
        "ix_endpoints_project_host_shape", "endpoints", ["project_id", "host", "shape"]
    )


def downgrade() -> None:
    op.add_column(
        "connectors",
        sa.Column(
            "capture_sessions", sa.Boolean(), nullable=False, server_default="true"
        ),
    )
    op.add_column(
        "connectors",
        sa.Column("queue_threshold", sa.Integer(), nullable=False, server_default="25"),
    )
    op.add_column(
        "connectors",
        sa.Column("quiet_minutes", sa.Integer(), nullable=False, server_default="5"),
    )
    op.add_column(
        "connectors",
        sa.Column(
            "sync_trigger",
            sa.String(length=16),
            nullable=False,
            server_default="manual",
        ),
    )
    op.add_column(
        "connectors",
        sa.Column("target_id", sa.dialects.postgresql.UUID(), nullable=True),
    )
    op.add_column(
        "connectors",
        sa.Column(
            "import_mode",
            sa.String(length=16),
            nullable=False,
            server_default="in_scope",
        ),
    )
    op.create_table(
        "connector_sessions",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "connector_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("connectors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client", sa.String(length=120), nullable=True),
        sa.Column("hosts", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("requests", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("novel", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_event_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_index("ix_endpoints_project_host_shape", table_name="endpoints")
    op.drop_column("endpoints", "shape")
