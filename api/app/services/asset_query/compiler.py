from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    and_,
    cast,
    exists,
    false,
    func,
    literal,
    or_,
    select,
    true,
    union_all,
)
from sqlalchemy.dialects.postgresql import INET, JSONB

from shared.definitions.asset_query import FLAGS, HOST_QUERY, FieldType, Op
from shared.models.http_asset import HttpAsset
from shared.models.port import Port
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .terms import (
    date_match,
    int_coerce,
    json_array_match,
    negate,
    number_match,
    scaled_coerce,
    string_match,
    tri_state,
)
from .values import asn_number, like, network, status_range, tsquery

_IPV4_RE = re.compile(r"^[0-9]{1,3}(\.[0-9]{1,3}){3}$")
_IP_CHARS_RE = r"^[0-9a-fA-F:.]+$"
_HEADER_WEIGHT = "A"
_BODY_WEIGHT = "B"


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
    return negate(matched) if cmp.op is Op.NE else matched


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
    return negate(matched) if cmp.op is Op.NE else matched


def _header(cmp: Compare):
    if cmp.sub:
        name = cmp.sub.lower().replace("-", "_")
        return string_match(
            cast(HttpAsset.response_headers, JSONB).op("->>")(name), cmp
        )
    if cmp.quoted:
        return string_match(HttpAsset.raw_response_header, cmp)
    return _tsv(cmp, _HEADER_WEIGHT)


def _cert(cmp: Compare, ctx: QueryContext):
    matched = or_(*[preds.cert_state(v.lower(), ctx.now) for v in cmp.values])
    return negate(matched) if cmp.op is Op.NE else matched


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
        branches.append(number_match(Subdomain.http_status, positive, int_coerce(cmp)))
    matched = or_(*branches)
    if cmp.op is Op.NE:
        return or_(Subdomain.http_status.is_(None), negate(matched))
    return matched


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
    "new": lambda _ctx: preds.is_new(),
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
    "vulnerable": lambda ctx: preds.host_vuln(ctx.scan_id),
    "kev": lambda ctx: preds.host_vuln(ctx.scan_id, Vulnerability.is_kev.is_(True)),
}


def _cdn(cmp: Compare):
    state = tri_state(cmp)
    if state is None:
        return string_match(Subdomain.cdn_name, cmp)
    return Subdomain.is_cdn.is_(state)


def _waf(cmp: Compare):
    state = tri_state(cmp)
    if state is None:
        return string_match(Subdomain.waf, cmp)
    return Subdomain.waf.isnot(None) if state else Subdomain.waf.is_(None)


def _issuer(cmp: Compare):
    return or_(
        string_match(HttpAsset.tls_issuer, cmp),
        string_match(HttpAsset.tls_issuer_org, cmp),
        string_match(HttpAsset.tls_issuer_cn, cmp),
    )


def _url():
    return func.coalesce(Subdomain.final_url, Subdomain.http_url)


_SUBDOMAIN_BUILDERS = {
    "host": lambda c, _ctx: string_match(Subdomain.name, c),
    "url": lambda c, _ctx: string_match(_url(), c),
    "cname": lambda c, _ctx: string_match(Subdomain.cname, c),
    "source": lambda c, _ctx: json_array_match(Subdomain.sources, c),
    "discovered": lambda c, ctx: date_match(
        Subdomain.discovered_at, c, ctx.now, future=False
    ),
    "status": lambda c, _ctx: _status(c),
    "title": lambda c, _ctx: string_match(Subdomain.page_title, c),
    "server": lambda c, _ctx: string_match(Subdomain.webserver, c),
    "tech": lambda c, _ctx: json_array_match(Subdomain.tech, c),
    "content_type": lambda c, _ctx: string_match(Subdomain.content_type, c),
    "size": lambda c, _ctx: number_match(
        Subdomain.content_length, c, scaled_coerce(c, FieldType.BYTES)
    ),
    "time": lambda c, _ctx: number_match(
        Subdomain.response_time, c, scaled_coerce(c, FieldType.DURATION)
    ),
    "favicon": lambda c, _ctx: string_match(Subdomain.favicon_hash, c),
    "ip": lambda c, _ctx: _ip(c),
    "asn": lambda c, _ctx: number_match(
        Subdomain.asn, c, lambda raw: asn_number(raw, c.start, c.end)
    ),
    "org": lambda c, _ctx: string_match(Subdomain.asn_org, c),
    "cdn": lambda c, _ctx: _cdn(c),
    "waf": lambda c, _ctx: _waf(c),
    "port": lambda c, _ctx: preds.port_match(
        number_match(Port.number, c, int_coerce(c))
    ),
    "service": lambda c, _ctx: preds.port_match(string_match(Port.service_name, c)),
    "cert": _cert,
    "cert.expires": lambda c, ctx: date_match(
        Subdomain.tls_not_after, c, ctx.now, future=True
    ),
    "vuln": lambda c, ctx: preds.host_vuln(
        ctx.scan_id, string_match(Vulnerability.severity, c)
    ),
    "cve": lambda c, ctx: preds.host_vuln(
        ctx.scan_id, json_array_match(Vulnerability.cve_ids, c)
    ),
    "is": _flag,
}

_ASSET_BUILDERS = {
    "path": lambda c, _ctx: string_match(HttpAsset.path, c),
    "words": lambda c, _ctx: number_match(HttpAsset.words, c, int_coerce(c)),
    "lines": lambda c, _ctx: number_match(HttpAsset.lines, c, int_coerce(c)),
    "redirect": lambda c, _ctx: string_match(HttpAsset.location, c),
    "content_hash": lambda c, _ctx: string_match(HttpAsset.content_hash, c),
    "body": lambda c, _ctx: _tsv(c, _BODY_WEIGHT),
    "header": lambda c, _ctx: _header(c),
    "cert.cn": lambda c, _ctx: string_match(HttpAsset.tls_subject_cn, c),
    "cert.san": lambda c, _ctx: json_array_match(HttpAsset.tls_sans, c),
    "cert.issuer": lambda c, _ctx: _issuer(c),
    "tls.version": lambda c, _ctx: string_match(HttpAsset.tls_version, c),
    "jarm": lambda c, _ctx: string_match(HttpAsset.jarm, c),
}

_FREE_TEXT_BUILDERS = {
    "cdn": lambda c, _ctx: string_match(Subdomain.cdn_name, c),
    "waf": lambda c, _ctx: string_match(Subdomain.waf, c),
    "url": lambda c, _ctx: string_match(Subdomain.final_url, c),
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
    for spec in HOST_QUERY.fields:
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
        return negate(compile_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_node(p, ctx) for p in node.parts])
    return true()


def compile_query(node: Node | None, ctx: QueryContext):
    return None if node is None else compile_node(node, ctx)
