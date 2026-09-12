"""composite discovered_at indexes and autovacuum thresholds on the result tables

Revision ID: f2a7c9d41b3e
Revises: e4d92a15b7c3
Create Date: 2026-09-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f2a7c9d41b3e"
down_revision: str | None = "e4d92a15b7c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KEYED = {
    "ports": ("ip", "number"),
    "ip_addresses": ("ip",),
    "vulnerabilities": ("fingerprint",),
}
_TABLES = ("subdomains", "endpoints", "ports", "ip_addresses", "vulnerabilities")
_STATS_TABLES = (*_TABLES, "http_assets", "interest_signals")
_AUTOVACUUM = (
    "autovacuum_analyze_scale_factor = 0.02, autovacuum_vacuum_scale_factor = 0.05"
)


def _indexes() -> list[tuple[str, str, tuple[str, ...]]]:
    out = []
    for table in _TABLES:
        out.append((f"ix_{table}_scan_discovered", table, ("scan_id", "discovered_at")))
        out.append(
            (f"ix_{table}_target_discovered", table, ("target_id", "discovered_at"))
        )
    for table, key in _KEYED.items():
        out.append(
            (
                f"ix_{table}_target_key_discovered",
                table,
                ("target_id", *key, "discovered_at"),
            )
        )
    return out


def upgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns in _indexes():
            op.execute(
                f"CREATE INDEX CONCURRENTLY IF NOT EXISTS {name} "
                f"ON {table} ({', '.join(columns)})"
            )
    for table in _STATS_TABLES:
        op.execute(f"ALTER TABLE {table} SET ({_AUTOVACUUM})")


def downgrade() -> None:
    for table in _STATS_TABLES:
        op.execute(
            f"ALTER TABLE {table} RESET "
            "(autovacuum_analyze_scale_factor, autovacuum_vacuum_scale_factor)"
        )
    with op.get_context().autocommit_block():
        for name, _table, _columns in _indexes():
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")
