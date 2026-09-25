"""scan deltas: row, first-seen and retired counts per scan, invalidated by revision triggers

Revision ID: 5d0c2a9e7b41
Revises: e3b81c5f27a4
Create Date: 2026-09-24 16:00:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from shared.definitions.surface import SurfaceDimension

revision: str = "5d0c2a9e7b41"
down_revision: str | None = "e3b81c5f27a4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = {
    "subdomains": SurfaceDimension.WEB_ASSETS.value,
    "endpoints": SurfaceDimension.ENDPOINTS.value,
    "ports": SurfaceDimension.SERVICES.value,
    "ip_addresses": SurfaceDimension.IPS.value,
    "vulnerabilities": SurfaceDimension.VULNERABILITIES.value,
    "software_cves": SurfaceDimension.SOFTWARE.value,
    "secrets": SurfaceDimension.SECRETS.value,
}

BUMP = """
CREATE FUNCTION scan_revisions_bump() RETURNS trigger
LANGUAGE plpgsql AS $fn$
BEGIN
    EXECUTE format($sql$
        WITH changed AS (
            SELECT target_id, scan_id, min(discovered_at) AS since
              FROM changed_rows
             GROUP BY target_id, scan_id
        ), floors AS (
            SELECT target_id, min(since) AS since FROM changed GROUP BY target_id
        ), later AS (
            SELECT s.id AS scan_id
              FROM scans s
              JOIN floors f ON f.target_id = s.target_id
             WHERE EXISTS (
                 SELECT 1 FROM %1$I t
                  WHERE t.scan_id = s.id AND t.discovered_at > f.since
             )
        ), affected AS (
            SELECT scan_id, 1 AS own FROM changed
            UNION ALL
            SELECT scan_id, 0 FROM later
        )
        INSERT INTO scan_revisions AS r (scan_id, dimension, rows_rev, history_rev)
        SELECT a.scan_id, %2$L, max(a.own), 1
          FROM affected a
          JOIN scans s ON s.id = a.scan_id
         GROUP BY a.scan_id
         ORDER BY a.scan_id
        ON CONFLICT (scan_id, dimension) DO UPDATE
           SET rows_rev = r.rows_rev + excluded.rows_rev,
               history_rev = r.history_rev + 1
    $sql$, TG_TABLE_NAME, TG_ARGV[0]);
    RETURN NULL;
END
$fn$
"""


def upgrade() -> None:
    op.create_table(
        "scan_revisions",
        sa.Column(
            "scan_id",
            sa.Uuid(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("rows_rev", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("history_rev", sa.BigInteger(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("scan_id", "dimension"),
    )
    op.create_table(
        "scan_deltas",
        sa.Column(
            "scan_id",
            sa.Uuid(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("history_rev", sa.BigInteger(), nullable=False),
        sa.Column("first_seen", sa.Integer(), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("first_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("scan_id", "dimension"),
    )
    op.create_table(
        "scan_retired",
        sa.Column(
            "scan_id",
            sa.Uuid(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prev_scan_id",
            sa.Uuid(),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("rows_rev", sa.BigInteger(), nullable=False),
        sa.Column("prev_rows_rev", sa.BigInteger(), nullable=False),
        sa.Column("retired", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("scan_id", "prev_scan_id", "dimension"),
    )
    op.create_index("ix_scan_retired_prev_scan_id", "scan_retired", ["prev_scan_id"])

    op.execute(BUMP)
    for table, dimension in TABLES.items():
        for event, alias in (("INSERT", "NEW"), ("DELETE", "OLD")):
            op.execute(
                f"CREATE TRIGGER {table}_revisions_{event.lower()} "
                f"AFTER {event} ON {table} "
                f"REFERENCING {alias} TABLE AS changed_rows "
                f"FOR EACH STATEMENT EXECUTE FUNCTION scan_revisions_bump('{dimension}')"
            )


def downgrade() -> None:
    for table in TABLES:
        for event in ("insert", "delete"):
            op.execute(f"DROP TRIGGER IF EXISTS {table}_revisions_{event} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS scan_revisions_bump()")
    op.drop_index("ix_scan_retired_prev_scan_id", table_name="scan_retired")
    op.drop_table("scan_retired")
    op.drop_table("scan_deltas")
    op.drop_table("scan_revisions")
