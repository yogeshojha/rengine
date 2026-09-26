from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import IP_FLAGS, IP_QUERY, Op
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

from . import predicates as preds
from .ast import Compare
from .scope import QueryScope
from .terms import (
    int_coerce,
    json_array_match,
    negate,
    number_match,
    string_match,
    target_overlap,
    tri_state,
)
from .values import PRIVATE_NETWORKS, asn_number, like, network
from .walk import flag_builder, walker

_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IPV4 = 4
_IPV6 = 6


@dataclass(frozen=True)
class IpQueryContext:
    scope: QueryScope
    now: datetime
    source: Any


def _inet(ctx: IpQueryContext):
    return preds.inet_of(ctx.source.c.ip)


def _within(ctx: IpQueryContext, cidr: str):
    return _inet(ctx).op("<<=")(cast(literal(cidr), INET))


def _host_exists(ctx: IpQueryContext, condition):
    return exists(
        select(1).where(
            ctx.scope.match(Subdomain.scan_id),
            condition,
            func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), ctx.source.c.ip),
        )
    )


def _port_exists(ctx: IpQueryContext, condition):
    return exists(
        select(1).where(
            ctx.scope.match(Port.scan_id), Port.ip == ctx.source.c.ip, condition
        )
    )


def _address(cmp: Compare, ctx: IpQueryContext):
    branches = []
    for raw in cmp.values:
        cidr = network(raw)
        if cidr is not None:
            branches.append(_within(ctx, str(cidr)))
        elif cmp.op is Op.EQ or _IPV4_RE.match(raw):
            branches.append(ctx.source.c.ip == raw)
        else:
            branches.append(ctx.source.c.ip.ilike(like(raw), escape="\\"))
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _cdn(cmp: Compare, ctx: IpQueryContext):
    state = tri_state(cmp)
    if state is None:
        return string_match(ctx.source.c.cdn_name, cmp)
    return ctx.source.c.is_cdn.is_(state)


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.address_is_new(ctx.source, ctx.scope),
    "alive": lambda ctx: ctx.source.c.is_alive.is_(True),
    "open": lambda ctx: ctx.source.c.port_count > 0,
    "sensitive": lambda ctx: ctx.source.c.sensitive.is_(True),
    "hosted": lambda ctx: ctx.source.c.host_count > 0,
    "web": lambda ctx: ctx.source.c.asset_count > 0,
    "cdn": lambda ctx: ctx.source.c.is_cdn.is_(True),
    "ptr": lambda ctx: func.jsonb_array_length(ctx.source.c.ptr_hostnames) > 0,
    "private": lambda ctx: or_(*[_within(ctx, n) for n in PRIVATE_NETWORKS]),
    "v4": lambda ctx: ctx.source.c.version == _IPV4,
    "v6": lambda ctx: ctx.source.c.version == _IPV6,
    "vulnerable": lambda ctx: preds.address_vuln(ctx.scope, ctx.source.c.ip),
    "kev": lambda ctx: preds.address_vuln(
        ctx.scope, ctx.source.c.ip, Vulnerability.is_kev.is_(True)
    ),
}

_IP_BUILDERS = {
    "target": lambda c, ctx: target_overlap(ctx.source.c.target_ids, c),
    "ip": _address,
    "ptr": lambda c, ctx: json_array_match(ctx.source.c.ptr_hostnames, c),
    "asn": lambda c, ctx: number_match(
        ctx.source.c.asn, c, lambda raw: asn_number(raw, c.start, c.end)
    ),
    "org": lambda c, ctx: string_match(ctx.source.c.asn_org, c),
    "country": lambda c, ctx: string_match(ctx.source.c.country, c),
    "prefix": lambda c, ctx: string_match(ctx.source.c.prefix, c),
    "cdn": _cdn,
    "port": lambda c, ctx: _port_exists(
        ctx, number_match(Port.number, c, int_coerce(c))
    ),
    "service": lambda c, ctx: _port_exists(ctx, string_match(Port.service_name, c)),
    "ports": lambda c, ctx: number_match(ctx.source.c.port_count, c, int_coerce(c)),
    "host": lambda c, ctx: _host_exists(ctx, string_match(Subdomain.name, c)),
    "hosts": lambda c, ctx: number_match(ctx.source.c.host_count, c, int_coerce(c)),
    "assets": lambda c, ctx: number_match(ctx.source.c.asset_count, c, int_coerce(c)),
    "vuln": lambda c, ctx: preds.address_vuln(
        ctx.scope, ctx.source.c.ip, string_match(Vulnerability.severity, c)
    ),
    "cve": lambda c, ctx: preds.address_vuln(
        ctx.scope, ctx.source.c.ip, json_array_match(Vulnerability.cve_ids, c)
    ),
    "is": flag_builder(_FLAG_BUILDERS, IP_FLAGS),
}


compile_ip_query = walker(IP_QUERY, _IP_BUILDERS)
