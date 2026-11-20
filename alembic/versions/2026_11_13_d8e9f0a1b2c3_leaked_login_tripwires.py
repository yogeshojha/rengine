"""leaked login tripwires

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "c7d8e9f0a1b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for column in ("employees_peak", "users_peak"):
        op.add_column(
            "target_infostealers",
            sa.Column(column, sa.INTEGER(), server_default="0", nullable=False),
        )
        op.alter_column("target_infostealers", column, server_default=None)
    op.execute(
        "UPDATE target_infostealers SET employees_peak = employees, users_peak = users"
    )

    op.create_table(
        "infostealer_sightings",
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("audience", sa.VARCHAR(length=16), nullable=False),
        sa.Column("host", sa.VARCHAR(length=500), nullable=False),
        sa.Column("first_seen", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("credentials_peak", sa.INTEGER(), nullable=False),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="infostealer_sightings_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "target_id", "audience", "host", name="infostealer_sightings_pkey"
        ),
    )
    op.execute(
        """
        INSERT INTO infostealer_sightings
            (target_id, audience, host, first_seen, credentials_peak)
        SELECT l.target_id, l.audience, l.host, r.checked_at, sum(l.credentials)
        FROM infostealer_logins l
        JOIN target_infostealers r ON r.target_id = l.target_id
        GROUP BY l.target_id, l.audience, l.host, r.checked_at
        """
    )

    op.create_table(
        "infostealer_changes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("target_id", sa.UUID(), nullable=False),
        sa.Column("checked_at", postgresql.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "previous_checked_at", postgresql.TIMESTAMP(timezone=True), nullable=True
        ),
        sa.Column("employees_from", sa.INTEGER(), nullable=False),
        sa.Column("employees_to", sa.INTEGER(), nullable=False),
        sa.Column("users_from", sa.INTEGER(), nullable=False),
        sa.Column("users_to", sa.INTEGER(), nullable=False),
        sa.Column("hosts", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["targets.id"],
            name="infostealer_changes_target_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="infostealer_changes_pkey"),
    )
    op.create_index(
        "ix_infostealer_changes_target_checked",
        "infostealer_changes",
        ["target_id", "checked_at"],
    )
    op.create_index(
        "ix_infostealer_changes_pending",
        "infostealer_changes",
        ["checked_at"],
        postgresql_where=sa.text("evaluated_at IS NULL"),
    )

    op.add_column(
        "tripwires", sa.Column("source", sa.VARCHAR(length=32), nullable=True)
    )
    op.add_column(
        "tripwires",
        sa.Column("params", sa.JSON(), server_default="{}", nullable=False),
    )
    op.alter_column("tripwires", "params", server_default=None)

    op.alter_column("tripwire_runs", "scan_id", nullable=True)
    op.add_column("tripwire_runs", sa.Column("event_id", sa.UUID(), nullable=True))
    op.create_index(
        "uq_tripwire_run_event",
        "tripwire_runs",
        ["tripwire_id", "event_id"],
        unique=True,
        postgresql_where=sa.text("event_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_tripwire_run_event", table_name="tripwire_runs")
    op.execute("DELETE FROM tripwire_runs WHERE scan_id IS NULL")
    op.drop_column("tripwire_runs", "event_id")
    op.alter_column("tripwire_runs", "scan_id", nullable=False)
    op.execute("DELETE FROM tripwires WHERE source IS NOT NULL")
    op.drop_column("tripwires", "params")
    op.drop_column("tripwires", "source")
    op.drop_index("ix_infostealer_changes_pending", table_name="infostealer_changes")
    op.drop_index(
        "ix_infostealer_changes_target_checked", table_name="infostealer_changes"
    )
    op.drop_table("infostealer_changes")
    op.drop_table("infostealer_sightings")
    op.drop_column("target_infostealers", "users_peak")
    op.drop_column("target_infostealers", "employees_peak")
