"""Software CVE statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from shared.definitions.asset_query import SOFTWARE_QUERY
from shared.models.software import SoftwareCve
from shared.services.asset_query import (
    QueryScope,
    SoftwareQueryContext,
    compile_software_query,
    parse_query,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.software import SoftwareFilter

_SORTS = {
    "rank": SoftwareCve.exploit_score,
    "cvss": SoftwareCve.cvss_score,
    "epss": SoftwareCve.epss_score,
    "cve": SoftwareCve.cve,
    "software": SoftwareCve.name,
    "host": SoftwareCve.host,
    "seen": SoftwareCve.discovered_at,
}


def severity_rank():
    return func.coalesce(SoftwareCve.cvss_score, 0.0)


def context(scope: QueryScope, now: datetime) -> SoftwareQueryContext:
    return SoftwareQueryContext(scope=scope, now=now)


def apply_filter(query, f: SoftwareFilter):
    if f.ids:
        query = query.where(SoftwareCve.id.in_(f.ids))
    return query


def order(query, f: SoftwareFilter):
    column = _SORTS.get((f.sort or "").lower())
    if column is None:
        return query.order_by(
            SoftwareCve.exploit_score.desc(),
            severity_rank().desc(),
            SoftwareCve.cve.desc(),
            SoftwareCve.id,
        )
    descending = (f.direction or "desc").lower() != "asc"
    ordered = column.desc() if descending else column.asc()
    return query.order_by(ordered, SoftwareCve.cve, SoftwareCve.id)


def scoped(scope: QueryScope, f: SoftwareFilter, columns=None):
    base = select(SoftwareCve) if columns is None else select(*columns)
    return apply_filter(base.where(scope.match(SoftwareCve.scan_id)), f)


def compiled(scope: QueryScope, f: SoftwareFilter, now: datetime):
    return compile_software_query(parse_query(f.q, SOFTWARE_QUERY), context(scope, now))


__all__ = [
    "apply_filter",
    "compiled",
    "context",
    "order",
    "scoped",
    "severity_rank",
]
