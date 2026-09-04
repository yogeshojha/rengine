from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import Text, and_, case, cast, desc, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.asset_query import MAX_GROUPS
from shared.definitions.ports import PORT_SOURCE_LABELS, SERVICE_CLASS_LABELS
from shared.definitions.vulnerabilities import (
    PROTOCOL_LABELS,
    SCANNER_LABELS,
    SEVERITY_LABELS,
    VULN_STATE_LABELS,
)
from shared.models.asset_query import QueryGroup, QueryGroups
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

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


_SERVICE_COLUMNS: dict[str, tuple[str, str, str]] = {
    "service": ("service_name", "service", "="),
    "class": ("service_class", "class", "="),
    "port": ("port", "port", ":"),
    "product": ("product", "product", "="),
    "ip": ("ip", "ip", "="),
    "asn": ("asn", "asn", ":"),
    "org": ("asn_org", "org", "="),
    "country": ("country", "country", "="),
    "source": ("source", "source", "="),
}
_SERVICE_LABELS: dict[str, dict[str, str]] = {
    "class": SERVICE_CLASS_LABELS,
    "source": PORT_SOURCE_LABELS,
}


async def build_service_groups(session: AsyncSession, base, key: str) -> QueryGroups:
    column = _SERVICE_COLUMNS.get(key)
    if column is None:
        return QueryGroups(dimension=key)
    attr, field, op = column

    scoped = base.subquery()
    value = getattr(scoped.c, attr).label("value")
    services = func.count()
    joined = (
        select(value, services.label("n"))
        .select_from(scoped)
        .where(value.isnot(None), cast(value, Text) != "")
    )
    rows_in_scope = await session.scalar(select(func.count()).select_from(scoped))
    covered, total = (
        await session.execute(
            joined.with_only_columns(services, func.count(func.distinct(value)))
        )
    ).one()
    rows = await session.execute(
        joined.group_by(value).order_by(desc("n"), value).limit(MAX_GROUPS)
    )

    labels = _SERVICE_LABELS.get(key, {})
    groups = [
        QueryGroup(
            value=str(raw),
            label=labels.get(str(raw)) or (f"AS{raw}" if key == "asn" else str(raw)),
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


_VULN_COLUMNS: dict[str, tuple[Any, str, str]] = {
    "template": (Vulnerability.template_id, "template", "="),
    "severity": (Vulnerability.severity, "severity", "="),
    "host": (Vulnerability.host, "host", "="),
    "location": (Vulnerability.matched_at, "location", "="),
    "type": (Vulnerability.protocol, "type", "="),
    "port": (Vulnerability.port, "port", ":"),
    "scanner": (Vulnerability.scanner, "scanner", "="),
}
_VULN_ARRAYS: dict[str, tuple[Any, str, str]] = {
    "tag": (Vulnerability.tags, "tag", "="),
    "cve": (Vulnerability.cve_ids, "cve", "="),
}
_VULN_LABELS: dict[str, dict[str, str]] = {
    "severity": SEVERITY_LABELS,
    "type": PROTOCOL_LABELS,
    "state": VULN_STATE_LABELS,
    "scanner": SCANNER_LABELS,
}


async def build_vuln_groups(
    session: AsyncSession, base, key: str, scan_id: UUID
) -> QueryGroups:
    """One row per finding; a multi-valued dimension puts a finding in several groups."""
    if key in _VULN_ARRAYS:
        column, field, op = _VULN_ARRAYS[key]
        value = func.jsonb_array_elements_text(cast(column, JSONB)).column_valued(
            f"{key}_value"
        )
    elif key == "state":
        value, field, op = preds.vuln_state(scan_id), "state", "="
    elif key in _VULN_COLUMNS:
        column, field, op = _VULN_COLUMNS[key]
        value = column
    else:
        return QueryGroups(dimension=key)

    scoped = base.subquery()
    labelled = value.label("value")
    findings = func.count(func.distinct(Vulnerability.id))
    joined = (
        select(labelled, findings.label("n"))
        .select_from(Vulnerability)
        .join(scoped, Vulnerability.id == scoped.c.id)
        .where(labelled.isnot(None), cast(labelled, Text) != "")
    )
    rows_in_scope = await session.scalar(select(func.count()).select_from(scoped))
    covered, total = (
        await session.execute(
            joined.with_only_columns(findings, func.count(func.distinct(labelled)))
        )
    ).one()
    rows = await session.execute(
        joined.group_by(labelled).order_by(desc("n"), labelled).limit(MAX_GROUPS)
    )

    labels = _VULN_LABELS.get(key, {})
    groups = [
        QueryGroup(
            value=str(raw),
            label=labels.get(str(raw)) or str(raw),
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
