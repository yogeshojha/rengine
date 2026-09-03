from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, cast, exists, false, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import SERVICE_FLAGS, SERVICE_QUERY, Op
from shared.definitions.ports import PortSource
from shared.models.subdomain import Subdomain

from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .terms import int_coerce, negate, number_match, string_match, tri_state
from .values import asn_number, like, network

_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IPV4 = 4
_IPV6 = 6
_PRIVATE_NETWORKS = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "127.0.0.0/8",
    "169.254.0.0/16",
    "100.64.0.0/10",
    "::1/128",
    "fc00::/7",
    "fe80::/10",
)


@dataclass(frozen=True)
class ServiceQueryContext:
    scan_id: UUID
    now: datetime
    source: Any


def _within(ctx: ServiceQueryContext, cidr: str):
    return ctx.source.c.inet.op("<<=")(cast(literal(cidr), INET))


def _host_exists(ctx: ServiceQueryContext, condition):
    return exists(
        select(1).where(
            Subdomain.scan_id == ctx.scan_id,
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


def _flag(cmp: Compare, ctx: ServiceQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(SERVICE_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_FLAG_BUILDERS = {
    "http": lambda ctx: ctx.source.c.is_http.is_(True),
    "tls": lambda ctx: ctx.source.c.tls.is_(True),
    "sensitive": lambda ctx: ctx.source.c.sensitive.is_(True),
    "named": lambda ctx: ctx.source.c.product.isnot(None),
    "passive": lambda ctx: ctx.source.c.source == PortSource.INTERNETDB.value,
    "confirmed": lambda ctx: ctx.source.c.source != PortSource.INTERNETDB.value,
    "cdn": lambda ctx: ctx.source.c.is_cdn.is_(True),
    "hosted": lambda ctx: ctx.source.c.host_count > 0,
    "private": lambda ctx: or_(*[_within(ctx, n) for n in _PRIVATE_NETWORKS]),
    "v4": lambda ctx: ctx.source.c.version == _IPV4,
    "v6": lambda ctx: ctx.source.c.version == _IPV6,
}

_SERVICE_BUILDERS = {
    "port": lambda c, ctx: number_match(ctx.source.c.port, c, int_coerce(c)),
    "service": lambda c, ctx: string_match(ctx.source.c.service_name, c),
    "class": lambda c, ctx: string_match(ctx.source.c.service_class, c),
    "protocol": lambda c, ctx: string_match(ctx.source.c.protocol, c),
    "source": lambda c, ctx: string_match(ctx.source.c.source, c),
    "product": lambda c, ctx: string_match(ctx.source.c.product, c),
    "version": lambda c, ctx: string_match(ctx.source.c.version, c),
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
    "is": _flag,
}


def compile_service_compare(cmp: Compare, ctx: ServiceQueryContext):
    builder = _SERVICE_BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched yet."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_service_term(term: Term, ctx: ServiceQueryContext):
    branches = []
    for spec in SERVICE_QUERY.fields:
        if not spec.free_text:
            continue
        cmp = Compare(
            name=spec.name,
            op=Op.MATCH,
            values=(term.value,),
            quoted=term.quoted,
            sub=None,
            start=term.start,
            end=term.end,
        )
        branches.append(_SERVICE_BUILDERS[spec.name](cmp, ctx))
    return or_(*branches) if branches else false()


def compile_service_node(node: Node, ctx: ServiceQueryContext):
    if isinstance(node, Term):
        return compile_service_term(node, ctx)
    if isinstance(node, Compare):
        return compile_service_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_service_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_service_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_service_node(p, ctx) for p in node.parts])
    return true()


def compile_service_query(node: Node | None, ctx: ServiceQueryContext):
    return None if node is None else compile_service_node(node, ctx)
