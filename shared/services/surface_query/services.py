"""Service statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    bindparam,
    column,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from shared.definitions.ports import SENSITIVE_PORTS
from shared.services.asset_query import (
    QueryScope,
    ServiceQueryContext,
    service_is_new,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.scan_correlation import ServiceFilter


_DERIVED_SQL = """
WITH hosts AS (
    SELECT ip, count(DISTINCT s.name) AS host_count
    FROM subdomains s, LATERAL jsonb_array_elements_text(cast(s.resolved_ips AS jsonb)) ip
    WHERE s.scan_id = ANY(:sids) GROUP BY ip
), addr AS (
    SELECT DISTINCT ON (ip) ip, asn, asn_org, country, prefix, is_cdn, cdn_name,
           scan_policy
    FROM ip_addresses WHERE scan_id = ANY(:sids)
    ORDER BY ip, discovered_at DESC
), web_top AS (
    -- the origin probe stores assets whose host is the address itself; a hostname
    -- describes the service, the default virtual host does not
    SELECT DISTINCT ON (ip, port) ip, port, status_code, url, title, screenshot_path
    FROM http_assets
    WHERE scan_id = ANY(:sids) AND ip IS NOT NULL
    ORDER BY ip, port, (host = ip) ASC, (scheme = 'https') DESC,
             (status_code BETWEEN 200 AND 399) DESC, url
), web_count AS (
    SELECT ip, port, count(DISTINCT host) AS web_count
    FROM http_assets
    WHERE scan_id = ANY(:sids) AND ip IS NOT NULL AND host <> ip GROUP BY ip, port
)
SELECT p.id AS id,
       p.scan_id AS scan_id,
       p.target_id AS target_id,
       p.discovered_at AS discovered_at,
       p.ip AS ip,
       CASE WHEN p.ip LIKE '%:%' THEN 6 ELSE 4 END AS version,
       cast(CASE WHEN p.ip ~ '^[0-9a-fA-F:.]+$' THEN p.ip END AS inet) AS inet,
       p.number AS port,
       p.protocol AS protocol,
       p.state AS state,
       p.service_name AS service_name,
       p.service_class AS service_class,
       p.source AS source,
       p.is_http AS is_http,
       p.tls AS tls,
       p.product AS product,
       p.version AS version_text,
       p.banner AS banner,
       (p.number = ANY(:sensitive_ports)) AS sensitive,
       x.asn AS asn,
       x.asn_org AS asn_org,
       x.country AS country,
       x.prefix AS prefix,
       coalesce(x.is_cdn, false) AS is_cdn,
       x.cdn_name AS cdn_name,
       x.scan_policy AS scan_policy,
       coalesce(h.host_count, 0) AS host_count,
       coalesce(c.web_count, 0) AS web_count,
       w.status_code AS status_code,
       w.url AS url,
       w.title AS title,
       w.screenshot_path AS screenshot_path
FROM ports p
LEFT JOIN addr x ON x.ip = p.ip
LEFT JOIN hosts h ON h.ip = p.ip
LEFT JOIN web_top w ON w.ip = p.ip AND w.port = p.number
LEFT JOIN web_count c ON c.ip = p.ip AND c.port = p.number
WHERE p.scan_id = ANY(:sids)
"""


def derived(scope: QueryScope):
    return (
        text(_DERIVED_SQL)
        .columns(
            column("id", PG_UUID(as_uuid=True)),
            column("scan_id", PG_UUID(as_uuid=True)),
            column("target_id", PG_UUID(as_uuid=True)),
            column("discovered_at", DateTime(timezone=True)),
            column("ip", String),
            column("version", Integer),
            column("inet", INET),
            column("port", Integer),
            column("protocol", String),
            column("state", String),
            column("service_name", String),
            column("service_class", String),
            column("source", String),
            column("is_http", Boolean),
            column("tls", Boolean),
            column("product", String),
            column("version_text", String),
            column("banner", String),
            column("sensitive", Boolean),
            column("asn", BigInteger),
            column("asn_org", String),
            column("country", String),
            column("prefix", String),
            column("is_cdn", Boolean),
            column("cdn_name", String),
            column("scan_policy", String),
            column("host_count", Integer),
            column("web_count", Integer),
            column("status_code", Integer),
            column("url", String),
            column("title", String),
            column("screenshot_path", String),
        )
        .bindparams(
            bindparam("sids", list(scope.ids), type_=ARRAY(PG_UUID(as_uuid=True))),
            bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
        )
        .cte("services")
    )


def apply_filter(query, d, f: ServiceFilter, scope: QueryScope):
    if f.classes:
        query = query.where(d.c.service_class.in_(f.classes))
    if f.ports:
        query = query.where(d.c.port.in_(f.ports))
    if f.services:
        query = query.where(d.c.service_name.in_(f.services))
    if f.sources:
        query = query.where(d.c.source.in_(f.sources))
    if f.asns:
        query = query.where(d.c.asn.in_(f.asns))
    if f.countries:
        query = query.where(d.c.country.in_(f.countries))
    if f.cdn == "yes":
        query = query.where(d.c.is_cdn.is_(True))
    elif f.cdn == "no":
        query = query.where(d.c.is_cdn.is_(False))
    if f.http == "yes":
        query = query.where(d.c.is_http.is_(True))
    elif f.http == "no":
        query = query.where(d.c.is_http.is_(False))
    if f.sensitive:
        query = query.where(d.c.sensitive.is_(True))
    if f.named:
        query = query.where(d.c.product.isnot(None))
    if f.new:
        query = query.where(service_is_new(d, scope))
    return query


def order(query, d, f: ServiceFilter):
    if f.sort == "exposure":
        return query.order_by(
            d.c.sensitive.desc(),
            d.c.is_http.asc(),
            d.c.host_count.desc(),
            d.c.inet.asc(),
            d.c.port.asc(),
        )
    col = {
        "port": d.c.port,
        "ip": d.c.inet,
        "service": d.c.service_name,
        "class": d.c.service_class,
        "product": d.c.product,
        "hosts": d.c.host_count,
        "asn": d.c.asn,
        "country": d.c.country,
        "status": d.c.status_code,
    }.get(f.sort, d.c.inet)
    primary = col.desc() if f.order == "desc" else col.asc()
    return query.order_by(primary.nulls_last(), d.c.inet.asc(), d.c.port.asc())


def scoped(scope: QueryScope, f: ServiceFilter, columns=None):
    d = derived(scope)
    base = select(d) if columns is None else select(*columns(d))
    return d, apply_filter(base, d, f, scope)


def context(scope: QueryScope, d, now: datetime) -> ServiceQueryContext:
    return ServiceQueryContext(scope=scope, now=now, source=d)
