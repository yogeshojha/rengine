"""Web asset statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.asset_query import HOST_QUERY
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.services.asset_query import (
    QueryContext,
    QueryScope,
    ScopeLike,
    compile_query,
    parse_query,
)
from shared.services.asset_query import (
    predicates as preds,
)

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from shared.models.subdomain import SubdomainFilter


def context(scope: QueryScope, now: datetime) -> QueryContext:
    return QueryContext(scope=scope, now=now)


def apply_filter(query, f: SubdomainFilter, now: datetime, scope: ScopeLike):
    if f.ids:
        query = query.where(Subdomain.id.in_(f.ids))
    if f.statuses:
        query = query.where(or_(*[preds.status_class(s) for s in f.statuses]))
    if f.tech:
        query = query.where(
            func.jsonb_exists_any(cast(Subdomain.tech, JSONB), pg_array(f.tech))
        )
    if f.sources:
        query = query.where(
            func.jsonb_exists_any(cast(Subdomain.sources, JSONB), pg_array(f.sources))
        )
    if f.cert:
        query = query.where(or_(*[preds.cert_state(c, now) for c in f.cert]))
    if f.hygiene:
        query = query.where(preds.hygiene(f.hygiene))
    if f.services:
        query = query.where(preds.port_match(Port.service_name.in_(f.services), scope))
    if f.cdn == "yes":
        query = query.where(Subdomain.is_cdn.is_(True))
    elif f.cdn == "no":
        query = query.where(Subdomain.is_cdn.is_(False))
    if f.waf == "present":
        query = query.where(Subdomain.waf.isnot(None))
    elif f.waf == "none":
        query = query.where(Subdomain.waf.is_(None))
    if f.live:
        query = query.where(preds.live())
    if f.screenshot:
        query = query.where(Subdomain.screenshot_path.isnot(None))
    if f.new:
        query = query.where(preds.is_new(scope))
    if f.issues:
        query = query.where(preds.issues(now, scope))
    return query


def order(query, f: SubdomainFilter):
    col = {
        "status": Subdomain.http_status,
        "size": Subdomain.content_length,
        "time": Subdomain.response_time,
        "title": Subdomain.page_title,
        "cert": Subdomain.tls_not_after,
        "discovered": Subdomain.discovered_at,
        "ip": cast(Subdomain.resolved_ips, JSONB).op("->>")(0),
    }.get(f.sort, Subdomain.name)
    primary = col.desc() if f.order == "desc" else col.asc()
    return query.order_by(
        primary.nulls_last(), Subdomain.name.asc(), Subdomain.id.asc()
    )


def scoped(
    project_id: UUID,
    scope: QueryScope,
    f: SubdomainFilter,
    now: datetime,
    columns=None,
):
    """The one definition of the filtered host set."""
    base = select(Subdomain) if columns is None else select(*columns)
    base = base.where(
        Subdomain.project_id == project_id, scope.match(Subdomain.scan_id)
    )
    return apply_filter(base, f, now, scope)


def compiled(scope: QueryScope, f: SubdomainFilter, now: datetime):
    return compile_query(parse_query(f.q, HOST_QUERY), context(scope, now))
