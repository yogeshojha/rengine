from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import cast, exists, func, literal, or_, select
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import SERVICE_FLAGS, SERVICE_QUERY, Op
from shared.definitions.ports import PortSource
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
    target_match,
    tri_state,
)
from .values import PRIVATE_NETWORKS, asn_number, like, network
from .walk import flag_builder, walker

_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IPV4 = 4
_IPV6 = 6


@dataclass(frozen=True)
class ServiceQueryContext:
    scope: QueryScope
    now: datetime
    source: Any


def _within(ctx: ServiceQueryContext, cidr: str):
    return ctx.source.c.inet.op("<<=")(cast(literal(cidr), INET))


def _host_exists(ctx: ServiceQueryContext, condition):
    return exists(
        select(1).where(
            ctx.scope.match(Subdomain.scan_id),
            condition,
            func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), ctx.source.c.ip),
        )
    )


def _address(cmp: Compare, ctx: ServiceQueryContext):
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


def _cdn(cmp: Compare, ctx: ServiceQueryContext):
    state = tri_state(cmp)
    if state is None:
        return string_match(ctx.source.c.cdn_name, cmp)
    return ctx.source.c.is_cdn.is_(state)


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.service_is_new(ctx.source, ctx.scope),
    "http": lambda ctx: ctx.source.c.is_http.is_(True),
    "tls": lambda ctx: ctx.source.c.tls.is_(True),
    "sensitive": lambda ctx: ctx.source.c.sensitive.is_(True),
    "named": lambda ctx: ctx.source.c.product.isnot(None),
    "passive": lambda ctx: ctx.source.c.source == PortSource.INTERNETDB.value,
    "confirmed": lambda ctx: ctx.source.c.source != PortSource.INTERNETDB.value,
    "cdn": lambda ctx: ctx.source.c.is_cdn.is_(True),
    "hosted": lambda ctx: ctx.source.c.host_count > 0,
    "private": lambda ctx: or_(*[_within(ctx, n) for n in PRIVATE_NETWORKS]),
    "v4": lambda ctx: ctx.source.c.version == _IPV4,
    "v6": lambda ctx: ctx.source.c.version == _IPV6,
    "vulnerable": lambda ctx: preds.service_vuln(
        ctx.scope, ctx.source.c.ip, ctx.source.c.port
    ),
    "kev": lambda ctx: preds.service_vuln(
        ctx.scope, ctx.source.c.ip, ctx.source.c.port, Vulnerability.is_kev.is_(True)
    ),
}

_SERVICE_BUILDERS = {
    "target": lambda c, ctx: target_match(ctx.source.c.target_id, c),
    "port": lambda c, ctx: number_match(ctx.source.c.port, c, int_coerce(c)),
    "service": lambda c, ctx: string_match(ctx.source.c.service_name, c),
    "class": lambda c, ctx: string_match(ctx.source.c.service_class, c),
    "protocol": lambda c, ctx: string_match(ctx.source.c.protocol, c),
    "source": lambda c, ctx: string_match(ctx.source.c.source, c),
    "product": lambda c, ctx: string_match(ctx.source.c.product, c),
    "version": lambda c, ctx: string_match(ctx.source.c.version_text, c),
    "banner": lambda c, ctx: string_match(ctx.source.c.banner, c),
    "ip": _address,
    "asn": lambda c, ctx: number_match(
        ctx.source.c.asn, c, lambda raw: asn_number(raw, c.start, c.end)
    ),
    "org": lambda c, ctx: string_match(ctx.source.c.asn_org, c),
    "country": lambda c, ctx: string_match(ctx.source.c.country, c),
    "cdn": _cdn,
    "host": lambda c, ctx: _host_exists(ctx, string_match(Subdomain.name, c)),
    "status": lambda c, ctx: number_match(ctx.source.c.status_code, c, int_coerce(c)),
    "vuln": lambda c, ctx: preds.service_vuln(
        ctx.scope,
        ctx.source.c.ip,
        ctx.source.c.port,
        string_match(Vulnerability.severity, c),
    ),
    "cve": lambda c, ctx: preds.service_vuln(
        ctx.scope,
        ctx.source.c.ip,
        ctx.source.c.port,
        json_array_match(Vulnerability.cve_ids, c),
    ),
    "is": flag_builder(_FLAG_BUILDERS, SERVICE_FLAGS),
}


compile_service_query = walker(SERVICE_QUERY, _SERVICE_BUILDERS)
