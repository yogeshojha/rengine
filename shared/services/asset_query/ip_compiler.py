from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, case, cast, exists, false, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import IP_FLAGS, IP_QUERY, Op
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .terms import (
    int_coerce,
    json_array_match,
    negate,
    number_match,
    string_match,
    tri_state,
)
from .values import asn_number, like, network

_IP_CHARS_RE = r"^[0-9a-fA-F:.]+$"
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
class IpQueryContext:
    scan_id: UUID
    now: datetime
    source: Any


def _inet(ctx: IpQueryContext):
    column = ctx.source.c.ip
    return cast(case((column.op("~")(_IP_CHARS_RE), column), else_=None), INET)


def _within(ctx: IpQueryContext, cidr: str):
    return _inet(ctx).op("<<=")(cast(literal(cidr), INET))


def _host_exists(ctx: IpQueryContext, condition):
    return exists(
        select(1).where(
            Subdomain.scan_id == ctx.scan_id,
            condition,
            func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), ctx.source.c.ip),
        )
    )


def _port_exists(ctx: IpQueryContext, condition):
    return exists(
        select(1).where(
            Port.scan_id == ctx.scan_id, Port.ip == ctx.source.c.ip, condition
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


def _flag(cmp: Compare, ctx: IpQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(IP_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.address_is_new(ctx.source.c.ip, ctx.scan_id),
    "alive": lambda ctx: ctx.source.c.is_alive.is_(True),
    "open": lambda ctx: ctx.source.c.port_count > 0,
    "sensitive": lambda ctx: ctx.source.c.sensitive.is_(True),
    "hosted": lambda ctx: ctx.source.c.host_count > 0,
    "web": lambda ctx: ctx.source.c.asset_count > 0,
    "cdn": lambda ctx: ctx.source.c.is_cdn.is_(True),
    "ptr": lambda ctx: func.jsonb_array_length(ctx.source.c.ptr_hostnames) > 0,
    "private": lambda ctx: or_(*[_within(ctx, n) for n in _PRIVATE_NETWORKS]),
    "v4": lambda ctx: ctx.source.c.version == _IPV4,
    "v6": lambda ctx: ctx.source.c.version == _IPV6,
    "vulnerable": lambda ctx: preds.address_vuln(ctx.scan_id, ctx.source.c.ip),
    "kev": lambda ctx: preds.address_vuln(
        ctx.scan_id, ctx.source.c.ip, Vulnerability.is_kev.is_(True)
    ),
}

_IP_BUILDERS = {
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
        ctx.scan_id, ctx.source.c.ip, string_match(Vulnerability.severity, c)
    ),
    "cve": lambda c, ctx: preds.address_vuln(
        ctx.scan_id, ctx.source.c.ip, json_array_match(Vulnerability.cve_ids, c)
    ),
    "is": _flag,
}


def compile_ip_compare(cmp: Compare, ctx: IpQueryContext):
    builder = _IP_BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched yet."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_ip_term(term: Term, ctx: IpQueryContext):
    branches = []
    for spec in IP_QUERY.fields:
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
        branches.append(_IP_BUILDERS[spec.name](cmp, ctx))
    return or_(*branches) if branches else false()


def compile_ip_node(node: Node, ctx: IpQueryContext):
    if isinstance(node, Term):
        return compile_ip_term(node, ctx)
    if isinstance(node, Compare):
        return compile_ip_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_ip_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_ip_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_ip_node(p, ctx) for p in node.parts])
    return true()


def compile_ip_query(node: Node | None, ctx: IpQueryContext):
    return None if node is None else compile_ip_node(node, ctx)
