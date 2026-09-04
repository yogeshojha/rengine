from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import Text, and_, case, cast, false, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import VULN_FLAGS, VULN_QUERY, Op
from shared.definitions.vulnerabilities import (
    EPSS_HIGH,
    SUPPRESSED_STATES,
    VulnState,
)
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.vulnerability import Vulnerability

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .terms import (
    date_match,
    int_coerce,
    json_array_match,
    negate,
    number_match,
    string_match,
)
from .values import asn_number, like, network

_IP_CHARS_RE = r"^[0-9a-fA-F:.]+$"
_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")


@dataclass(frozen=True)
class VulnQueryContext:
    scan_id: UUID
    now: datetime


def _inet():
    column = Vulnerability.ip
    return cast(case((column.op("~")(_IP_CHARS_RE), column), else_=None), INET)


def _address(cmp: Compare, _ctx: VulnQueryContext):
    branches = []
    for raw in cmp.values:
        cidr = network(raw)
        if cidr is not None:
            branches.append(_inet().op("<<=")(cast(literal(str(cidr)), INET)))
        elif cmp.op is Op.EQ or _IPV4_RE.match(raw):
            branches.append(Vulnerability.ip == raw)
        else:
            branches.append(Vulnerability.ip.ilike(like(raw), escape="\\"))
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _asset(condition):
    """A property of the HTTP asset the finding sits on."""
    return Vulnerability.http_asset_id.in_(select(HttpAsset.id).where(condition))


def _asset_by_host(ctx: VulnQueryContext, condition):
    return or_(
        _asset(condition),
        Vulnerability.host.in_(
            select(HttpAsset.host).where(HttpAsset.scan_id == ctx.scan_id, condition)
        ),
    )


def _address_meta(ctx: VulnQueryContext, condition):
    """A property of the address the finding sits on."""
    return Vulnerability.ip.in_(
        select(IpAddress.ip).where(IpAddress.scan_id == ctx.scan_id, condition)
    )


def _flag(cmp: Compare, ctx: VulnQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(VULN_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.vuln_is_new(ctx.scan_id),
    "kev": lambda _ctx: Vulnerability.is_kev.is_(True),
    "cve": lambda _ctx: func.jsonb_array_length(cast(Vulnerability.cve_ids, JSONB)) > 0,
    "exploitable": lambda _ctx: or_(
        Vulnerability.is_kev.is_(True), Vulnerability.epss_score >= EPSS_HIGH
    ),
    "proven": lambda _ctx: and_(
        Vulnerability.request.isnot(None), Vulnerability.response.isnot(None)
    ),
    "extracted": lambda _ctx: func.jsonb_array_length(
        cast(Vulnerability.extracted_results, JSONB)
    )
    > 0,
    "web": lambda _ctx: Vulnerability.http_asset_id.isnot(None),
    "cdn": lambda ctx: _asset(
        and_(HttpAsset.scan_id == ctx.scan_id, HttpAsset.is_cdn.is_(True))
    ),
    "triaged": lambda ctx: preds.vuln_state(ctx.scan_id) != VulnState.OPEN.value,
    "open": lambda ctx: preds.vuln_state(ctx.scan_id) == VulnState.OPEN.value,
    "suppressed": lambda ctx: preds.vuln_state(ctx.scan_id).in_(SUPPRESSED_STATES),
}


def _float_coerce(raw: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        msg = f"{raw!r} is not a number."
        raise QuerySyntaxError(msg, 0, 0) from exc


def _state_match(cmp: Compare, ctx: VulnQueryContext):
    state = preds.vuln_state(ctx.scan_id)
    values = [v.lower().replace("-", "_").replace(" ", "_") for v in cmp.values]
    matched = state.in_(values)
    return negate(matched) if cmp.op is Op.NE else matched


_VULN_BUILDERS = {
    "name": lambda c, _ctx: string_match(Vulnerability.template_name, c),
    "template": lambda c, _ctx: string_match(Vulnerability.template_id, c),
    "severity": lambda c, _ctx: string_match(Vulnerability.severity, c),
    "type": lambda c, _ctx: string_match(Vulnerability.protocol, c),
    "scanner": lambda c, _ctx: string_match(Vulnerability.scanner, c),
    "tag": lambda c, _ctx: json_array_match(Vulnerability.tags, c),
    "matcher": lambda c, _ctx: string_match(Vulnerability.matcher_name, c),
    "extracted": lambda c, _ctx: string_match(
        cast(Vulnerability.extracted_results, Text), c
    ),
    "author": lambda c, _ctx: json_array_match(Vulnerability.authors, c),
    "cve": lambda c, _ctx: json_array_match(Vulnerability.cve_ids, c),
    "cwe": lambda c, _ctx: json_array_match(Vulnerability.cwe_ids, c),
    "cvss": lambda c, _ctx: number_match(Vulnerability.cvss_score, c, _float_coerce),
    "epss": lambda c, _ctx: number_match(Vulnerability.epss_score, c, _float_coerce),
    "host": lambda c, _ctx: string_match(Vulnerability.host, c),
    "location": lambda c, _ctx: string_match(Vulnerability.matched_at, c),
    "ip": _address,
    "port": lambda c, _ctx: number_match(Vulnerability.port, c, int_coerce(c)),
    "status": lambda c, ctx: _asset(
        and_(
            HttpAsset.scan_id == ctx.scan_id,
            number_match(HttpAsset.status_code, c, int_coerce(c)),
        )
    ),
    "tech": lambda c, ctx: _asset_by_host(ctx, json_array_match(HttpAsset.tech, c)),
    "asn": lambda c, ctx: _address_meta(
        ctx, number_match(IpAddress.asn, c, lambda raw: asn_number(raw, c.start, c.end))
    ),
    "country": lambda c, ctx: _address_meta(ctx, string_match(IpAddress.country, c)),
    "state": _state_match,
    "seen": lambda c, ctx: date_match(
        Vulnerability.discovered_at, c, ctx.now, future=False
    ),
    "is": _flag,
}


def compile_vuln_compare(cmp: Compare, ctx: VulnQueryContext):
    builder = _VULN_BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched yet."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_vuln_term(term: Term, ctx: VulnQueryContext):
    branches = []
    for spec in VULN_QUERY.fields:
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
        branches.append(_VULN_BUILDERS[spec.name](cmp, ctx))
    return or_(*branches) if branches else false()


def compile_vuln_node(node: Node, ctx: VulnQueryContext):
    if isinstance(node, Term):
        return compile_vuln_term(node, ctx)
    if isinstance(node, Compare):
        return compile_vuln_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_vuln_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_vuln_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_vuln_node(p, ctx) for p in node.parts])
    return true()


def compile_vuln_query(node: Node | None, ctx: VulnQueryContext):
    return None if node is None else compile_vuln_node(node, ctx)
