from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import (
    Text,
    and_,
    cast,
    exists,
    false,
    func,
    literal,
    not_,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.asset_query import FIELDS, FLAGS, FieldType, Op
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .values import (
    asn_number,
    is_relative,
    like,
    moment,
    network,
    scaled_number,
    split_range,
    status_range,
    tsquery,
)

_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IP_CHARS_RE = r"^[0-9a-fA-F:.]+$"
_TRUTHY = {"yes", "true", "1", "any", "present"}
_FALSY = {"no", "false", "0", "none", "absent"}
_HEADER_WEIGHT = "A"
_BODY_WEIGHT = "B"
_ONE_DAY = timedelta(days=1)


def _negate(expr):
    return not_(func.coalesce(expr, false()))


@dataclass(frozen=True)
class QueryContext:
    scan_id: UUID
    now: datetime


@dataclass(frozen=True)
class Compiled:
    where: object | None = None
    asset: object | None = None

    def flatten(self, ctx: QueryContext):
        parts = [self.where] if self.where is not None else []
        if self.asset is not None:
            parts.append(preds.asset_match(ctx.scan_id, self.asset))
        return and_(*parts) if parts else true()


def _string(col, cmp: Compare):
    if cmp.op is Op.MATCH:
        return or_(*[col.ilike(like(v), escape="\\") for v in cmp.values])
    lowered = [v.lower() for v in cmp.values]
    if cmp.op is Op.EQ:
        return func.lower(col).in_(lowered)
    if cmp.op is Op.NE:
        return or_(col.is_(None), _negate(func.lower(col).in_(lowered)))
    matched = or_(*[col.op("~*")(v) for v in cmp.values])
    if cmp.op is Op.RE:
        return matched
    return or_(col.is_(None), _negate(matched))


def _number(col, cmp: Compare, coerce):
    if cmp.op in (Op.MATCH, Op.EQ, Op.NE):
        branches = []
        for raw in cmp.values:
            bounds = split_range(raw)
            if bounds is None:
                branches.append(col == coerce(raw))
            else:
                branches.append(
                    and_(col >= coerce(bounds[0]), col <= coerce(bounds[1]))
                )
        matched = or_(*branches)
        return or_(col.is_(None), _negate(matched)) if cmp.op is Op.NE else matched
    return _threshold(col, cmp.op, coerce(cmp.values[0]))


def _threshold(col, op: Op, value):
    if op is Op.GT:
        return col > value
    if op is Op.GTE:
        return col >= value
    if op is Op.LT:
        return col < value
    if op is Op.LTE:
        return col <= value
    if op is Op.NE:
        return or_(col.is_(None), col != value)
    return col == value


def _date(col, cmp: Compare, ctx: QueryContext, *, future: bool):
    raw = cmp.values[0]
    instant = moment(raw, cmp.start, cmp.end)
    if not is_relative(raw):
        if cmp.op in (Op.MATCH, Op.EQ):
            return and_(col >= instant, col < instant + _ONE_DAY)
        return _threshold(col, cmp.op, instant)
    span = ctx.now - instant
    boundary = ctx.now + span if future else ctx.now - span
    if cmp.op in (Op.MATCH, Op.EQ):
        return col <= boundary if future else col >= boundary
    op = cmp.op if future else _FLIPPED.get(cmp.op, cmp.op)
    return _threshold(col, op, boundary)


_FLIPPED = {Op.GT: Op.LT, Op.GTE: Op.LTE, Op.LT: Op.GT, Op.LTE: Op.GTE}


def _json_array(col, cmp: Compare):
    if cmp.op is Op.EQ:
        return func.jsonb_exists_any(cast(col, JSONB), pg_array(list(cmp.values)))
    if cmp.op in (Op.RE, Op.NRE):
        element = (
            func.jsonb_array_elements_text(cast(col, JSONB))
            .table_valued("value")
            .alias("element")
        )
        found = exists(
            select(1)
            .select_from(element)
            .where(or_(*[element.c.value.op("~*")(v) for v in cmp.values]))
        )
        return _negate(found) if cmp.op is Op.NRE else found
    matched = or_(*[cast(col, Text).ilike(like(v), escape="\\") for v in cmp.values])
    return _negate(matched) if cmp.op is Op.NE else matched


def _ip(cmp: Compare):
    branches = []
    for raw in cmp.values:
        cidr = network(raw)
        if cidr is not None:
            branches.append(_within(str(cidr)))
        elif cmp.op is Op.EQ or _IPV4_RE.match(raw):
            branches.append(func.jsonb_exists(cast(Subdomain.resolved_ips, JSONB), raw))
        else:
            branches.append(preds.ip_text().ilike(like(raw), escape="\\"))
    matched = or_(*branches)
    return _negate(matched) if cmp.op is Op.NE else matched


def _within(cidr: str):
    element = (
        func.jsonb_array_elements_text(cast(Subdomain.resolved_ips, JSONB))
        .table_valued("value")
        .alias("resolved_ip")
    )
    return exists(
        select(1)
        .select_from(element)
        .where(
            element.c.value.op("~")(_IP_CHARS_RE),
            cast(element.c.value, INET).op("<<=")(cast(literal(cidr), INET)),
        )
    )


def _tri_state(cmp: Compare) -> bool | None:
    if len(cmp.values) != 1:
        return None
    value = cmp.values[0].lower()
    if value in _TRUTHY:
        return True
    return False if value in _FALSY else None


def _tsv(cmp: Compare, weight: str):
    branches = []
    for raw in cmp.values:
        query = tsquery(raw, weight, prefix=not cmp.quoted)
        if query:
            branches.append(
                HttpAsset.search_tsv.op("@@")(func.to_tsquery("simple", query))
            )
    if not branches:
        return false()
    matched = or_(*branches)
    return _negate(matched) if cmp.op is Op.NE else matched


def _header(cmp: Compare):
    if cmp.sub:
        name = cmp.sub.lower().replace("-", "_")
        return _string(cast(HttpAsset.response_headers, JSONB).op("->>")(name), cmp)
    if cmp.quoted:
        return _string(HttpAsset.raw_response_header, cmp)
    return _tsv(cmp, _HEADER_WEIGHT)


def _cert(cmp: Compare, ctx: QueryContext):
    matched = or_(*[preds.cert_state(v.lower(), ctx.now) for v in cmp.values])
    return _negate(matched) if cmp.op is Op.NE else matched


def _status(cmp: Compare):
    branches = []
    numeric: list[str] = []
    for raw in cmp.values:
        bounds = status_range(raw)
        if bounds is not None:
            branches.append(
                and_(
                    Subdomain.http_status >= bounds[0],
                    Subdomain.http_status <= bounds[1],
                )
            )
        elif raw.lower() == "none":
            branches.append(Subdomain.http_status.is_(None))
        else:
            numeric.append(raw)
    if numeric:
        positive = Compare(
            name=cmp.name,
            op=Op.MATCH if cmp.op is Op.NE else cmp.op,
            values=tuple(numeric),
            quoted=cmp.quoted,
            sub=cmp.sub,
            start=cmp.start,
            end=cmp.end,
        )
        branches.append(_number(Subdomain.http_status, positive, _int(cmp)))
    matched = or_(*branches)
    if cmp.op is Op.NE:
        return or_(Subdomain.http_status.is_(None), _negate(matched))
    return matched


def _int(cmp: Compare):
    def coerce(raw: str) -> int:
        return int(scaled_number(raw, FieldType.NUMBER, cmp.start, cmp.end))

    return coerce


def _scaled(cmp: Compare, kind: FieldType):
    def coerce(raw: str) -> float:
        return scaled_number(raw, kind, cmp.start, cmp.end)

    return coerce


def _flag(cmp: Compare, ctx: QueryContext):
    branches = []
    for raw in cmp.values:
        name = raw.lower()
        builder = _FLAG_BUILDERS.get(name)
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_FLAG_BUILDERS = {
    "live": lambda _ctx: preds.live(),
    "web": lambda _ctx: Subdomain.http_status.isnot(None),
    "new": lambda _ctx: not_(preds.seen_earlier()),
    "resolved": lambda _ctx: preds.resolved(),
    "auth": lambda _ctx: preds.auth(),
    "cdn": lambda _ctx: Subdomain.is_cdn.is_(True),
    "waf": lambda _ctx: Subdomain.waf.isnot(None),
    "screenshot": lambda _ctx: Subdomain.screenshot_path.isnot(None),
    "important": lambda _ctx: Subdomain.is_important.is_(True),
    "wildcard": lambda _ctx: Subdomain.is_wildcard.is_(True),
    "issue": lambda ctx: preds.issues(ctx.now),
    "sensitive": lambda _ctx: preds.sensitive(),
    "http2": lambda ctx: preds.asset_match(
        ctx.scan_id, HttpAsset.supports_http2.is_(True)
    ),
    "redirect": lambda _ctx: and_(
        Subdomain.final_url.isnot(None), Subdomain.final_url != Subdomain.http_url
    ),
}


def _cdn(cmp: Compare):
    state = _tri_state(cmp)
    if state is None:
        return _string(Subdomain.cdn_name, cmp)
    return Subdomain.is_cdn.is_(state)


def _waf(cmp: Compare):
    state = _tri_state(cmp)
    if state is None:
        return _string(Subdomain.waf, cmp)
    return Subdomain.waf.isnot(None) if state else Subdomain.waf.is_(None)


def _issuer(cmp: Compare):
    return or_(
        _string(HttpAsset.tls_issuer, cmp),
        _string(HttpAsset.tls_issuer_org, cmp),
        _string(HttpAsset.tls_issuer_cn, cmp),
    )


def _url():
    return func.coalesce(Subdomain.final_url, Subdomain.http_url)


_SUBDOMAIN_BUILDERS = {
    "host": lambda c, _ctx: _string(Subdomain.name, c),
    "url": lambda c, _ctx: _string(_url(), c),
    "cname": lambda c, _ctx: _string(Subdomain.cname, c),
    "source": lambda c, _ctx: _json_array(Subdomain.sources, c),
    "discovered": lambda c, ctx: _date(Subdomain.discovered_at, c, ctx, future=False),
    "status": lambda c, _ctx: _status(c),
    "title": lambda c, _ctx: _string(Subdomain.page_title, c),
    "server": lambda c, _ctx: _string(Subdomain.webserver, c),
    "tech": lambda c, _ctx: _json_array(Subdomain.tech, c),
    "content_type": lambda c, _ctx: _string(Subdomain.content_type, c),
    "size": lambda c, _ctx: _number(
        Subdomain.content_length, c, _scaled(c, FieldType.BYTES)
    ),
    "time": lambda c, _ctx: _number(
        Subdomain.response_time, c, _scaled(c, FieldType.DURATION)
    ),
    "favicon": lambda c, _ctx: _string(Subdomain.favicon_hash, c),
    "ip": lambda c, _ctx: _ip(c),
    "asn": lambda c, _ctx: _number(
        Subdomain.asn, c, lambda raw: asn_number(raw, c.start, c.end)
    ),
    "org": lambda c, _ctx: _string(Subdomain.asn_org, c),
    "cdn": lambda c, _ctx: _cdn(c),
    "waf": lambda c, _ctx: _waf(c),
    "port": lambda c, _ctx: preds.port_match(_number(Port.number, c, _int(c))),
    "service": lambda c, _ctx: preds.port_match(_string(Port.service_name, c)),
    "cert": _cert,
    "cert.expires": lambda c, ctx: _date(Subdomain.tls_not_after, c, ctx, future=True),
    "is": _flag,
}

_ASSET_BUILDERS = {
    "path": lambda c, _ctx: _string(HttpAsset.path, c),
    "words": lambda c, _ctx: _number(HttpAsset.words, c, _int(c)),
    "lines": lambda c, _ctx: _number(HttpAsset.lines, c, _int(c)),
    "redirect": lambda c, _ctx: _string(HttpAsset.location, c),
    "body": lambda c, _ctx: _tsv(c, _BODY_WEIGHT),
    "header": lambda c, _ctx: _header(c),
    "cert.cn": lambda c, _ctx: _string(HttpAsset.tls_subject_cn, c),
    "cert.san": lambda c, _ctx: _json_array(HttpAsset.tls_sans, c),
    "cert.issuer": lambda c, _ctx: _issuer(c),
    "tls.version": lambda c, _ctx: _string(HttpAsset.tls_version, c),
    "jarm": lambda c, _ctx: _string(HttpAsset.jarm, c),
}

_FREE_TEXT_BUILDERS = {
    "cdn": lambda c, _ctx: _string(Subdomain.cdn_name, c),
    "waf": lambda c, _ctx: _string(Subdomain.waf, c),
    "url": lambda c, _ctx: _string(Subdomain.final_url, c),
    "favicon": lambda c, _ctx: Subdomain.favicon_hash == c.values[0],
}


def compile_compare(cmp: Compare, ctx: QueryContext) -> Compiled:
    builder = _SUBDOMAIN_BUILDERS.get(cmp.name)
    if builder is not None:
        return Compiled(where=builder(cmp, ctx))
    builder = _ASSET_BUILDERS.get(cmp.name)
    if builder is not None:
        return Compiled(asset=builder(cmp, ctx))
    msg = f"Field {cmp.name!r} cannot be searched yet."
    raise QuerySyntaxError(msg, cmp.start, cmp.end)


def compile_term(term: Term, ctx: QueryContext):
    scope = Subdomain.scan_id == ctx.scan_id
    branches = []
    assets = []
    for spec in FIELDS:
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
        override = _FREE_TEXT_BUILDERS.get(spec.name)
        if override is not None:
            branches.append(override(cmp, ctx))
        elif spec.name in _ASSET_BUILDERS:
            assets.append(_ASSET_BUILDERS[spec.name](cmp, ctx))
        else:
            branches.append(_SUBDOMAIN_BUILDERS[spec.name](cmp, ctx))
    if assets:
        branches.append(preds.asset_match(ctx.scan_id, or_(*assets)))
    if not branches:
        return false()
    reachable = union_all(
        *[
            select(Subdomain.id).where(scope, branch).correlate(None)
            for branch in branches
        ]
    ).subquery()
    return Subdomain.id.in_(select(reachable.c.id))


def compile_node(node: Node, ctx: QueryContext):
    if isinstance(node, Term):
        return compile_term(node, ctx)
    if isinstance(node, Compare):
        return compile_compare(node, ctx).flatten(ctx)
    if isinstance(node, Not):
        return _negate(compile_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_node(p, ctx) for p in node.parts])
    return true()


def compile_query(node: Node | None, ctx: QueryContext):
    return None if node is None else compile_node(node, ctx)
