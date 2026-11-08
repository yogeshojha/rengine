"""ANALYZE on the result tables."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.models.endpoint import Endpoint
from shared.models.http_asset import HttpAsset
from shared.models.interest import InterestSignal
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

RESULT_TABLES: tuple[str, ...] = tuple(
    model.__tablename__
    for model in (
        Subdomain,
        Endpoint,
        Port,
        IpAddress,
        Vulnerability,
        HttpAsset,
        InterestSignal,
    )
)


ANALYZE_SHARE = 0.01
ANALYZE_MIN_ROWS = 1000

_DUE_SQL = text(
    """
    SELECT relname FROM pg_stat_user_tables
     WHERE schemaname = current_schema() AND relname = ANY(:tables)
       AND (COALESCE(last_analyze, last_autoanalyze) IS NULL
            OR n_mod_since_analyze >= GREATEST(:floor, :share * n_live_tup))
     ORDER BY relname
    """
)


def due_tables(session: Session) -> list[str]:
    return list(
        session.execute(
            _DUE_SQL,
            {
                "tables": list(RESULT_TABLES),
                "floor": ANALYZE_MIN_ROWS,
                "share": ANALYZE_SHARE,
            },
        ).scalars()
    )


def analyze_result_tables(session: Session) -> list[str]:
    try:
        due = due_tables(session)
        if due:
            session.execute(text(f"ANALYZE (SKIP_LOCKED) {', '.join(due)}"))
        session.commit()
        return due
    except Exception:
        session.rollback()
        raise
