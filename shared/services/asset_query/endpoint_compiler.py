from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, cast, false, func, or_, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array

from shared.definitions.asset_query import ENDPOINT_FLAGS, ENDPOINT_QUERY, FieldType, Op
from shared.definitions.endpoints import (
    STATIC_CLASSES,
    EndpointClass,
    EndpointSource,
    PathInterest,
)
from shared.models.endpoint import Endpoint
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
)

_SENSITIVE_INTEREST = (
    PathInterest.VCS.value,
    PathInterest.SECRETS.value,
    PathInterest.BACKUP.value,
)
_MISSING = (404, 410)


@dataclass(frozen=True)
class EndpointQueryContext:
    scan_id: UUID
    now: datetime


def _has_any(column, names: list[str]):
    return func.jsonb_exists_any(cast(column, JSONB), pg_array(names))


def _flag(cmp: Compare, ctx: EndpointQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(ENDPOINT_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.endpoint_is_new(ctx.scan_id),
    "param": lambda _ctx: Endpoint.param_count > 0,
    "probed": lambda _ctx: Endpoint.is_probed.is_(True),
    "live": lambda _ctx: and_(
        Endpoint.status_code >= preds.HTTP_OK,
        Endpoint.status_code < preds.HTTP_CLIENT,
    ),
    "redirect": lambda _ctx: and_(
        Endpoint.status_code >= preds.HTTP_REDIRECT,
        Endpoint.status_code < preds.HTTP_CLIENT,
    ),
    "auth": lambda _ctx: Endpoint.status_code.in_(preds.AUTH_STATUS),
    "missing": lambda _ctx: Endpoint.status_code.in_(_MISSING),
    "api": lambda _ctx: Endpoint.endpoint_class == EndpointClass.API.value,
    "js": lambda _ctx: Endpoint.endpoint_class == EndpointClass.SCRIPT.value,
    "static": lambda _ctx: Endpoint.endpoint_class.in_(tuple(STATIC_CLASSES)),
    "interesting": lambda _ctx: (
        func.jsonb_array_length(cast(Endpoint.interest, JSONB)) > 0
    ),
    "sensitive": lambda _ctx: _has_any(Endpoint.interest, list(_SENSITIVE_INTEREST)),
    "orphan": lambda _ctx: preds.endpoint_orphan(),
    "archive-only": lambda _ctx: preds.endpoint_archive_only(),
    "linked": lambda _ctx: preds.endpoint_linked(),
    "crawled": lambda _ctx: preds.endpoint_source(EndpointSource.CRAWL.value),
    "root": lambda _ctx: and_(Endpoint.path == "/", Endpoint.param_count == 0),
    "titled": lambda _ctx: and_(Endpoint.title.isnot(None), Endpoint.title != ""),
    "vulnerable": lambda ctx: preds.endpoint_vuln(ctx.scan_id),
    "kev": lambda ctx: preds.endpoint_vuln(ctx.scan_id, Vulnerability.is_kev.is_(True)),
}


def _dir_match(cmp: Compare, _ctx: EndpointQueryContext):
    """`dir:` matches a whole branch of the tree; `dir=` matches that one folder."""
    branches = []
    for raw in cmp.values:
        value = raw if raw.startswith("/") else f"/{raw}"
        prefix = value if value.endswith("/") else f"{value}/"
        if cmp.op is Op.EQ:
            branches.append(Endpoint.dir_path == prefix)
            continue
        escaped = prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        branches.append(Endpoint.dir_path.like(f"{escaped}%", escape="\\"))
    matched = or_(*branches)
    return negate(matched) if cmp.op is Op.NE else matched


def _status_match(cmp: Compare, _ctx: EndpointQueryContext):
    """Values may mix named classes and numbers, as the host grammar allows."""
    classes = {*preds.STATUS_BUCKETS, "none"}
    named = [v for v in cmp.values if v.lower() in classes]
    numeric = [v for v in cmp.values if v.lower() not in classes]
    branches = [preds.endpoint_status_class(v.lower()) for v in named]
    if numeric:
        rest = replace(cmp, values=tuple(numeric), op=Op.MATCH)
        branches.append(number_match(Endpoint.status_code, rest, int_coerce(rest)))
    matched = or_(*branches) if branches else false()
    if cmp.op is Op.NE:
        return negate(matched)
    if cmp.op in (Op.MATCH, Op.EQ) or named:
        return matched
    return number_match(Endpoint.status_code, cmp, int_coerce(cmp))


def _vuln_severity(cmp: Compare, ctx: EndpointQueryContext):
    matched = preds.endpoint_vuln(
        ctx.scan_id, string_match(Vulnerability.severity, cmp)
    )
    return negate(matched) if cmp.op is Op.NE else matched


def _vuln_cve(cmp: Compare, ctx: EndpointQueryContext):
    matched = preds.endpoint_vuln(
        ctx.scan_id, json_array_match(Vulnerability.cve_ids, cmp)
    )
    return negate(matched) if cmp.op is Op.NE else matched


_ENDPOINT_BUILDERS = {
    "url": lambda c, _ctx: string_match(Endpoint.url, c),
    "path": lambda c, _ctx: string_match(Endpoint.path, c),
    "dir": _dir_match,
    "file": lambda c, _ctx: string_match(Endpoint.filename, c),
    "ext": lambda c, _ctx: string_match(Endpoint.extension, c),
    "host": lambda c, _ctx: string_match(Endpoint.host, c),
    "port": lambda c, _ctx: number_match(Endpoint.port, c, int_coerce(c)),
    "scheme": lambda c, _ctx: string_match(Endpoint.scheme, c),
    "depth": lambda c, _ctx: number_match(Endpoint.depth, c, int_coerce(c)),
    "class": lambda c, _ctx: string_match(Endpoint.endpoint_class, c),
    "param": lambda c, _ctx: json_array_match(Endpoint.params, c),
    "params": lambda c, _ctx: number_match(Endpoint.param_count, c, int_coerce(c)),
    "interest": lambda c, _ctx: json_array_match(Endpoint.interest, c),
    "status": _status_match,
    "type": lambda c, _ctx: string_match(Endpoint.content_type, c),
    "title": lambda c, _ctx: string_match(Endpoint.title, c),
    "length": lambda c, _ctx: number_match(
        Endpoint.content_length, c, scaled_coerce(c, FieldType.BYTES)
    ),
    "words": lambda c, _ctx: number_match(Endpoint.words, c, int_coerce(c)),
    "tech": lambda c, _ctx: json_array_match(Endpoint.tech, c),
    "method": lambda c, _ctx: json_array_match(Endpoint.methods, c),
    "source": lambda c, _ctx: json_array_match(Endpoint.sources, c),
    "from": lambda c, _ctx: string_match(Endpoint.found_on, c),
    "seen": lambda c, ctx: date_match(Endpoint.discovered_at, c, ctx.now, future=False),
    "vuln": _vuln_severity,
    "cve": _vuln_cve,
    "is": _flag,
}


def compile_endpoint_compare(cmp: Compare, ctx: EndpointQueryContext):
    builder = _ENDPOINT_BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched yet."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_endpoint_term(term: Term, ctx: EndpointQueryContext):
    branches = []
    for spec in ENDPOINT_QUERY.fields:
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
        branches.append(_ENDPOINT_BUILDERS[spec.name](cmp, ctx))
    return or_(*branches) if branches else false()


def compile_endpoint_node(node: Node, ctx: EndpointQueryContext):
    if isinstance(node, Term):
        return compile_endpoint_term(node, ctx)
    if isinstance(node, Compare):
        return compile_endpoint_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_endpoint_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_endpoint_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_endpoint_node(p, ctx) for p in node.parts])
    return true()


def compile_endpoint_query(node: Node | None, ctx: EndpointQueryContext):
    return None if node is None else compile_endpoint_node(node, ctx)
