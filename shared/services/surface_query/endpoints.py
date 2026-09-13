"""Endpoint statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB

from shared.definitions.asset_query import ENDPOINT_QUERY
from shared.definitions.endpoints import STATIC_CLASSES, STATIC_EXTENSIONS
from shared.models.endpoint import Endpoint
from shared.services.asset_query import (
    EndpointQueryContext,
    QueryScope,
    compile_endpoint_query,
    endpoint_is_new,
    endpoint_status_class,
    parse_query,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.endpoint import EndpointFilter


def static_clause():
    return or_(
        Endpoint.endpoint_class.in_(tuple(STATIC_CLASSES)),
        func.coalesce(Endpoint.extension, "").in_(tuple(STATIC_EXTENSIONS)),
    )


def context(scope: QueryScope, now: datetime) -> EndpointQueryContext:
    return EndpointQueryContext(scope=scope, now=now)


def apply_filter(query, f: EndpointFilter, scope: QueryScope):
    if f.host:
        query = query.where(Endpoint.host == f.host)
    if f.dir_path:
        prefix = f.dir_path if f.dir_path.endswith("/") else f"{f.dir_path}/"
        if f.subtree:
            escaped = (
                prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            query = query.where(Endpoint.dir_path.like(f"{escaped}%", escape="\\"))
        else:
            query = query.where(Endpoint.dir_path == prefix)
    if f.endpoint_class:
        query = query.where(Endpoint.endpoint_class == f.endpoint_class)
    if f.source:
        query = query.where(func.jsonb_exists(cast(Endpoint.sources, JSONB), f.source))
    if f.interest:
        query = query.where(
            func.jsonb_exists(cast(Endpoint.interest, JSONB), f.interest)
        )
    if f.status_class:
        query = query.where(endpoint_status_class(f.status_class))
    if f.probed is not None:
        query = query.where(Endpoint.is_probed.is_(f.probed))
    if f.new:
        query = query.where(endpoint_is_new(scope))
    if f.hide_static:
        query = query.where(~static_clause())
    return query


def order(query, f: EndpointFilter):
    if f.sort == "relevance":
        return query.order_by(
            (func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0)
            .desc()
            .nulls_last(),
            (Endpoint.param_count > 0).desc(),
            Endpoint.is_probed.desc(),
            endpoint_status_class("2xx").desc(),
            Endpoint.depth.asc(),
            Endpoint.host.asc(),
            Endpoint.path.asc(),
        )
    column = {
        "path": Endpoint.path,
        "url": Endpoint.url,
        "host": Endpoint.host,
        "status": Endpoint.status_code,
        "length": Endpoint.content_length,
        "params": Endpoint.param_count,
        "depth": Endpoint.depth,
        "seen": Endpoint.discovered_at,
        "class": Endpoint.endpoint_class,
    }.get(f.sort, Endpoint.path)
    primary = column.desc() if f.direction == "desc" else column.asc()
    return query.order_by(
        primary.nulls_last(), Endpoint.host.asc(), Endpoint.path.asc()
    )


def scoped(scope: QueryScope, f: EndpointFilter, columns=None):
    base = select(Endpoint) if columns is None else select(*columns)
    base = base.where(scope.match(Endpoint.scan_id))
    return apply_filter(base, f, scope)


def compiled(scope: QueryScope, f: EndpointFilter, now: datetime):
    return compile_endpoint_query(parse_query(f.q, ENDPOINT_QUERY), context(scope, now))


__all__ = [
    "apply_filter",
    "compiled",
    "context",
    "order",
    "scoped",
    "static_clause",
]
