from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, cast, false, func, literal, or_, true
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import SOFTWARE_FLAGS, SOFTWARE_QUERY, Op
from shared.definitions.software import Caveat, Confidence, VersionSource
from shared.models.software import SoftwareCve

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .scope import QueryScope
from .terms import (
    date_match,
    int_coerce,
    negate,
    number_match,
    string_match,
    target_match,
)
from .values import like, network


@dataclass(frozen=True)
class SoftwareQueryContext:
    scope: QueryScope
    now: datetime


LIKELY_EPSS = 0.088
_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IP_CHARS_RE = "^[0-9a-fA-F:.]+$"


def _float_coerce(raw: str) -> float:
    try:
        return float(raw)
    except ValueError as exc:
        msg = f"{raw!r} is not a number."
        raise QuerySyntaxError(msg, 0, 0) from exc


def _inet():
    column = SoftwareCve.ip
    return cast(case((column.op("~")(_IP_CHARS_RE), column), else_=None), INET)


def _address(cmp: Compare, _ctx: SoftwareQueryContext):
    branches = []
    for raw in cmp.values:
        cidr = network(raw)
        if cidr is not None:
            branches.append(_inet().op("<<=")(cast(literal(str(cidr)), INET)))
        elif cmp.op is Op.EQ or _IPV4_RE.match(raw):
            branches.append(SoftwareCve.ip == raw)
        else:
            branches.append(SoftwareCve.ip.ilike(like(raw), escape="\\"))
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _caveat(cmp: Compare, _ctx: SoftwareQueryContext):
    branches = [
        func.jsonb_exists(cast(SoftwareCve.caveats, JSONB), raw.lower())
        for raw in cmp.values
    ]
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _overdue(ctx: SoftwareQueryContext):
    return and_(
        SoftwareCve.kev_due_date.isnot(None),
        SoftwareCve.kev_due_date < ctx.now.date(),
    )


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.software_is_new(ctx.scope),
    "kev": lambda _ctx: SoftwareCve.is_kev.is_(True),
    "ransomware": lambda _ctx: SoftwareCve.kev_ransomware.is_(True),
    "overdue": _overdue,
    "likely": lambda _ctx: SoftwareCve.epss_score >= LIKELY_EPSS,
    "firm": lambda _ctx: SoftwareCve.confidence == Confidence.HIGH.value,
    "conditional": lambda _ctx: func.jsonb_exists(
        cast(SoftwareCve.caveats, JSONB), Caveat.CONDITIONAL.value
    ),
    "backport": lambda _ctx: func.jsonb_exists(
        cast(SoftwareCve.caveats, JSONB), Caveat.BACKPORT.value
    ),
    "fingerprinted": lambda _ctx: (
        SoftwareCve.version_source == VersionSource.FINGERPRINT.value
    ),
    "stated": lambda _ctx: SoftwareCve.version_source == VersionSource.BANNER.value,
    "web": lambda _ctx: SoftwareCve.http_asset_id.isnot(None),
    "service": lambda _ctx: SoftwareCve.port_id.isnot(None),
}


def _flag(cmp: Compare, ctx: SoftwareQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(SOFTWARE_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_BUILDERS = {
    "target": lambda c, _ctx: target_match(SoftwareCve.target_id, c),
    "cve": lambda c, _ctx: string_match(SoftwareCve.cve, c),
    "software": lambda c, _ctx: string_match(SoftwareCve.name, c),
    "product": lambda c, _ctx: string_match(SoftwareCve.product, c),
    "vendor": lambda c, _ctx: string_match(SoftwareCve.vendor, c),
    "version": lambda c, _ctx: string_match(SoftwareCve.version, c),
    "source": lambda c, _ctx: string_match(SoftwareCve.version_source, c),
    "severity": lambda c, _ctx: string_match(SoftwareCve.severity, c),
    "cvss": lambda c, _ctx: number_match(SoftwareCve.cvss_score, c, _float_coerce),
    "epss": lambda c, _ctx: number_match(SoftwareCve.epss_score, c, _float_coerce),
    "rank": lambda c, _ctx: number_match(SoftwareCve.exploit_score, c, int_coerce(c)),
    "confidence": lambda c, _ctx: string_match(SoftwareCve.confidence, c),
    "caveat": _caveat,
    "host": lambda c, _ctx: string_match(SoftwareCve.host, c),
    "ip": _address,
    "port": lambda c, _ctx: number_match(SoftwareCve.port, c, int_coerce(c)),
    "seen": lambda c, ctx: date_match(
        SoftwareCve.discovered_at, c, ctx.now, future=False
    ),
    "is": _flag,
}


def compile_software_compare(cmp: Compare, ctx: SoftwareQueryContext):
    builder = _BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_software_term(term: Term, ctx: SoftwareQueryContext):
    branches = []
    for spec in SOFTWARE_QUERY.fields:
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
        branches.append(_BUILDERS[spec.name](cmp, ctx))
    return or_(*branches) if branches else false()


def compile_software_node(node: Node, ctx: SoftwareQueryContext):
    if isinstance(node, Term):
        return compile_software_term(node, ctx)
    if isinstance(node, Compare):
        return compile_software_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_software_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_software_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_software_node(p, ctx) for p in node.parts])
    return true()


def compile_software_query(node: Node | None, ctx: SoftwareQueryContext):
    return None if node is None else compile_software_node(node, ctx)
