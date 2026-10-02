"""Address statement building, shared by the api's search and the worker's export."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    and_,
    bindparam,
    column,
    exists,
    not_,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from shared.definitions.asset_query import IP_QUERY
from shared.definitions.ports import SENSITIVE_PORTS
from shared.models.port import Port
from shared.services.asset_query import (
    IpQueryContext,
    QueryScope,
    compile_ip_query,
    inet_of,
    parse_query,
)

if TYPE_CHECKING:
    from datetime import datetime

    from shared.models.scan_correlation import IpGroupFilter


_DERIVED_SQL = """
WITH facts AS (
    SELECT ip, s.target_id, s.name AS host, NULL::integer AS number,
           NULL::bigint AS asn, NULL::varchar AS asn_org, NULL::boolean AS is_cdn,
           NULL::varchar AS cdn_name, NULL::timestamptz AS seen, 1 AS kind
    FROM subdomains s, LATERAL json_array_elements_text(s.resolved_ips) ip
    WHERE s.scan_id = ANY(:sids) AND s.resolved_ips::text <> '[]'
    UNION ALL
    SELECT ip, target_id, NULL, number, NULL, NULL, NULL, NULL, NULL, 2
    FROM ports WHERE scan_id = ANY(:sids)
    UNION ALL
    SELECT ip, target_id, NULL, NULL, asn, asn_org, is_cdn, cdn_name, NULL, 3
    FROM http_assets WHERE scan_id = ANY(:sids) AND ip IS NOT NULL
    UNION ALL
    SELECT ip, target_id, NULL, NULL, NULL, NULL, NULL, NULL, discovered_at, 4
    FROM ip_addresses WHERE scan_id = ANY(:sids)
), folded AS (
    SELECT ip,
           array_agg(DISTINCT target_id) AS target_ids,
           min(seen) AS first_seen,
           count(DISTINCT (target_id, host)) FILTER (WHERE kind = 1) AS host_count,
           count(*) FILTER (WHERE kind = 2) AS port_count,
           bool_or(number = ANY(:sensitive_ports)) AS sensitive,
           count(*) FILTER (WHERE kind = 3) AS asset_count,
           max(asn) AS asn, max(asn_org) AS asn_org, bool_or(is_cdn) AS is_cdn,
           max(cdn_name) AS cdn_name
    FROM facts GROUP BY ip
), addr AS (
    SELECT DISTINCT ON (ip) ip, asn, asn_org, country, prefix,
           is_cdn, cdn_name, is_alive, ptr_hostnames
    FROM ip_addresses WHERE scan_id = ANY(:sids)
    ORDER BY ip, discovered_at DESC
)
SELECT f.ip AS ip,
       f.target_ids AS target_ids,
       f.first_seen AS first_seen,
       CASE WHEN f.ip LIKE '%:%' THEN 6 ELSE 4 END AS version,
       coalesce(x.asn, f.asn) AS asn,
       coalesce(x.asn_org, f.asn_org) AS asn_org,
       x.country AS country,
       x.prefix AS prefix,
       coalesce(x.is_cdn, f.is_cdn, false) AS is_cdn,
       coalesce(x.cdn_name, f.cdn_name) AS cdn_name,
       coalesce(x.is_alive, f.asset_count > 0 OR f.port_count > 0, false) AS is_alive,
       coalesce(cast(x.ptr_hostnames AS jsonb), '[]'::jsonb) AS ptr_hostnames,
       f.host_count AS host_count,
       f.port_count AS port_count,
       coalesce(f.sensitive, false) AS sensitive,
       f.asset_count AS asset_count
FROM folded f
LEFT JOIN addr x ON x.ip = f.ip
"""


def derived(scope: QueryScope):
    return (
        text(_DERIVED_SQL)
        .columns(
            column("ip", String),
            column("target_ids", ARRAY(PG_UUID(as_uuid=True))),
            column("first_seen", DateTime(timezone=True)),
            column("version", Integer),
            column("asn", BigInteger),
            column("asn_org", String),
            column("country", String),
            column("prefix", String),
            column("is_cdn", Boolean),
            column("cdn_name", String),
            column("is_alive", Boolean),
            column("ptr_hostnames", JSONB),
            column("host_count", Integer),
            column("port_count", Integer),
            column("sensitive", Boolean),
            column("asset_count", Integer),
        )
        .bindparams(
            bindparam("sids", list(scope.ids), type_=ARRAY(PG_UUID(as_uuid=True))),
            bindparam("sensitive_ports", SENSITIVE_PORTS, type_=ARRAY(Integer)),
        )
        .cte("ip_groups")
    )


def port_exists(scope: QueryScope, d, cond):
    return exists(select(1).where(scope.match(Port.scan_id), Port.ip == d.c.ip, cond))


def exposure_bucket(d, bucket: str):
    if bucket == "open":
        return d.c.port_count > 0
    alive = d.c.is_alive.is_(True)
    if bucket == "responding":
        return and_(d.c.port_count == 0, alive)
    if bucket == "quiet":
        return and_(d.c.port_count == 0, not_(alive))
    return None


def apply_filter(q, d, f: IpGroupFilter, scope: QueryScope):
    if f.ids:
        q = q.where(d.c.ip.in_(f.ids))
    if f.exposure:
        buckets = [exposure_bucket(d, b) for b in f.exposure]
        q = q.where(or_(*[b for b in buckets if b is not None]))
    if f.asns:
        q = q.where(d.c.asn.in_(f.asns))
    if f.countries:
        q = q.where(d.c.country.in_(f.countries))
    if f.ports:
        q = q.where(port_exists(scope, d, Port.number.in_(f.ports)))
    if f.services:
        q = q.where(port_exists(scope, d, Port.service_name.in_(f.services)))
    if f.cdn == "yes":
        q = q.where(d.c.is_cdn.is_(True))
    elif f.cdn == "no":
        q = q.where(d.c.is_cdn.is_(False))
    if f.alive == "yes":
        q = q.where(d.c.is_alive.is_(True))
    elif f.alive == "no":
        q = q.where(d.c.is_alive.is_(False))
    if f.version in (4, 6):
        q = q.where(d.c.version == f.version)
    if f.sensitive:
        q = q.where(d.c.sensitive.is_(True))
    if f.hosted:
        q = q.where(d.c.host_count > 0)
    if f.open:
        q = q.where(d.c.port_count > 0)
    return q


def order(q, d, f: IpGroupFilter):
    ip_num = inet_of(d.c.ip)
    col = {
        "hosts": d.c.host_count,
        "ports": d.c.port_count,
        "assets": d.c.asset_count,
        "asn": d.c.asn,
        "country": d.c.country,
    }.get(f.sort, ip_num)
    primary = col.desc() if f.order == "desc" else col.asc()
    return q.order_by(primary.nulls_last(), ip_num.asc())


def scoped(scope: QueryScope, f: IpGroupFilter, columns=None):
    d = derived(scope)
    base = select(d) if columns is None else select(*columns(d))
    return d, apply_filter(base, d, f, scope)


def context(scope: QueryScope, d, now: datetime) -> IpQueryContext:
    return IpQueryContext(scope=scope, now=now, source=d)


def compiled(scope: QueryScope, f: IpGroupFilter, now: datetime, source):
    return compile_ip_query(parse_query(f.q, IP_QUERY), context(scope, source, now))
