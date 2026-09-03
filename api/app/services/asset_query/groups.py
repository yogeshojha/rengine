from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import Text, and_, case, cast, desc, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.asset_query import MAX_GROUPS
from shared.models.asset_query import QueryGroup, QueryGroups
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain

from . import predicates as preds

_STATUS_LABELS = {
    "2xx": "2xx OK",
    "3xx": "3xx Redirect",
    "4xx": "4xx Client",
    "5xx": "5xx Server",
}
_NEEDS_QUOTE = re.compile(r'[\s()"\[\]:=><~]')


def _token(field: str, op: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{escaped}"' if _NEEDS_QUOTE.search(value) or not value else value
    return f"{field}{op}{quoted}"


def _status_case():
    return case(
        *[
            (
                (Subdomain.http_status >= lo) & (Subdomain.http_status < hi),
                bucket,
            )
            for bucket, (lo, hi) in preds.STATUS_BUCKETS.items()
        ],
        else_=None,
    )


_DIMENSIONS: dict[str, tuple[Callable[[], Any], str, str, bool]] = {
    "ip": (
        lambda: func.jsonb_array_elements_text(
            cast(Subdomain.resolved_ips, JSONB)
        ).column_valued("ip_value"),
        "ip",
        ":",
        False,
    ),
    "tech": (
        lambda: func.jsonb_array_elements_text(
            cast(Subdomain.tech, JSONB)
        ).column_valued("tech_value"),
        "tech",
        "=",
        False,
    ),
    "favicon": (lambda: Subdomain.favicon_hash, "favicon", "=", False),
    "title": (lambda: Subdomain.page_title, "title", "=", False),
    "cname": (lambda: Subdomain.cname, "cname", "=", False),
    "server": (lambda: Subdomain.webserver, "server", "=", False),
    "cdn": (lambda: Subdomain.cdn_name, "cdn", "=", False),
    "status": (_status_case, "status", ":", False),
    "content_hash": (lambda: HttpAsset.content_hash, "content_hash", "=", True),
    "jarm": (lambda: HttpAsset.jarm, "jarm", "=", True),
    "cert.issuer": (lambda: HttpAsset.tls_issuer, "cert.issuer", "=", True),
}


def _dimension(key: str):
    found = _DIMENSIONS.get(key)
    if found is None:
        return None
    build, field, op, asset = found
    return build(), field, op, asset


async def build_groups(session: AsyncSession, base, key: str) -> QueryGroups:
    dimension = _dimension(key)
    if dimension is None:
        return QueryGroups(dimension=key)
    column, field, op, asset = dimension

    scoped = base.subquery()
    value = column.label("value")
    joined = (
        select(value, func.count(func.distinct(Subdomain.id)).label("n"))
        .select_from(Subdomain)
        .join(scoped, Subdomain.id == scoped.c.id)
    )
    if asset:
        joined = joined.join(
            HttpAsset,
            and_(
                HttpAsset.scan_id == Subdomain.scan_id,
                HttpAsset.host == Subdomain.name,
            ),
        )
    joined = joined.where(value.isnot(None), value != "")
    hosts = await session.scalar(select(func.count()).select_from(scoped))
    covered, total = (
        await session.execute(
            joined.with_only_columns(
                func.count(func.distinct(Subdomain.id)),
                func.count(func.distinct(value)),
            )
        )
    ).one()
    rows = await session.execute(
        joined.group_by(value).order_by(desc("n"), value).limit(MAX_GROUPS)
    )

    groups = [
        QueryGroup(
            value=str(raw),
            label=_STATUS_LABELS.get(str(raw), str(raw))
            if key == "status"
            else str(raw),
            count=int(n),
            query=_token(field, op, str(raw)),
        )
        for raw, n in rows.all()
    ]
    counted = int(total or 0)
    return QueryGroups(
        dimension=key,
        groups=groups,
        total_groups=counted,
        truncated=counted > len(groups),
        rows=int(hosts or 0),
        covered=int(covered or 0),
    )


_IP_COLUMNS: dict[str, tuple[str, str, str]] = {
    "asn": ("asn", "asn", ":"),
    "org": ("asn_org", "org", "="),
    "prefix": ("prefix", "prefix", "="),
    "country": ("country", "country", "="),
    "cdn": ("cdn_name", "cdn", "="),
}
_IP_PORT_COLUMNS: dict[str, tuple[Any, str, str]] = {
    "port": (Port.number, "port", ":"),
    "service": (Port.service_name, "service", "="),
}


async def build_ip_groups(
    session: AsyncSession, base, key: str, scan_id: UUID
) -> QueryGroups:
    scoped = base.subquery()
    joined = None
    if key in _IP_COLUMNS:
        attr, field, op = _IP_COLUMNS[key]
        value = getattr(scoped.c, attr).label("value")
        joined = select(value).select_from(scoped)
    elif key in _IP_PORT_COLUMNS:
        column, field, op = _IP_PORT_COLUMNS[key]
        value = column.label("value")
        joined = (
            select(value)
            .select_from(scoped)
            .join(Port, and_(Port.scan_id == scan_id, Port.ip == scoped.c.ip))
        )
    if joined is None:
        return QueryGroups(dimension=key)

    addresses = func.count(func.distinct(scoped.c.ip))
    joined = joined.add_columns(addresses.label("n")).where(
        value.isnot(None), cast(value, Text) != ""
    )
    rows_in_scope = await session.scalar(select(func.count()).select_from(scoped))
    covered, total = (
        await session.execute(
            joined.with_only_columns(addresses, func.count(func.distinct(value)))
        )
    ).one()
    rows = await session.execute(
        joined.group_by(value).order_by(desc("n"), value).limit(MAX_GROUPS)
    )

    groups = [
        QueryGroup(
            value=str(raw),
            label=f"AS{raw}" if key == "asn" else str(raw),
            count=int(n),
            query=_token(field, op, str(raw)),
        )
        for raw, n in rows.all()
    ]
    counted = int(total or 0)
    return QueryGroups(
        dimension=key,
        groups=groups,
        total_groups=counted,
        truncated=counted > len(groups),
        rows=int(rows_in_scope or 0),
        covered=int(covered or 0),
    )
