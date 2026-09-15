from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, false, or_, true

from shared.definitions.asset_query import SECRET_FLAGS, SECRET_QUERY, Op
from shared.definitions.secrets import SecretState
from shared.models.secret import Secret

from . import predicates as preds
from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .scope import QueryScope
from .terms import date_match, negate, string_match, target_match


@dataclass(frozen=True)
class SecretQueryContext:
    scope: QueryScope
    now: datetime


_FLAG_BUILDERS = {
    "new": lambda ctx: preds.secret_is_new(ctx.scope),
    "exposed": lambda _ctx: Secret.state == SecretState.EXPOSED.value,
    "public": lambda _ctx: Secret.state == SecretState.PUBLIC.value,
    "expired": lambda _ctx: Secret.state == SecretState.EXPIRED.value,
    "secret": lambda _ctx: Secret.is_secret.is_(True),
    "shared": lambda _ctx: Secret.hosts > 1,
}


def _flag(cmp: Compare, ctx: SecretQueryContext):
    branches = []
    for raw in cmp.values:
        builder = _FLAG_BUILDERS.get(raw.lower())
        if builder is None:
            msg = f"Unknown flag {raw!r}."
            hint = f"Try one of: {', '.join(SECRET_FLAGS)}"
            raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
        branches.append(builder(ctx))
    return or_(*branches)


_BUILDERS = {
    "target": lambda c, _ctx: target_match(Secret.target_id, c),
    "secret": lambda c, _ctx: string_match(Secret.kind, c),
    "fingerprint": lambda c, _ctx: string_match(Secret.fingerprint, c),
    "group": lambda c, _ctx: string_match(Secret.group, c),
    "vendor": lambda c, _ctx: string_match(Secret.vendor, c),
    "subject": lambda c, _ctx: string_match(Secret.subject, c),
    "state": lambda c, _ctx: string_match(Secret.state, c),
    "source": lambda c, _ctx: string_match(Secret.source, c),
    "host": lambda c, _ctx: string_match(Secret.host, c),
    "url": lambda c, _ctx: string_match(Secret.url, c),
    "seen": lambda c, ctx: date_match(Secret.discovered_at, c, ctx.now, future=False),
    "is": _flag,
}


def compile_secret_compare(cmp: Compare, ctx: SecretQueryContext):
    builder = _BUILDERS.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def compile_secret_term(term: Term, ctx: SecretQueryContext):
    branches = []
    for spec in SECRET_QUERY.fields:
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


def compile_secret_node(node: Node, ctx: SecretQueryContext):
    if isinstance(node, Term):
        return compile_secret_term(node, ctx)
    if isinstance(node, Compare):
        return compile_secret_compare(node, ctx)
    if isinstance(node, Not):
        return negate(compile_secret_node(node.part, ctx))
    if isinstance(node, And):
        return and_(*[compile_secret_node(p, ctx) for p in node.parts])
    if isinstance(node, Or):
        return or_(*[compile_secret_node(p, ctx) for p in node.parts])
    return true()


def compile_secret_query(node: Node | None, ctx: SecretQueryContext):
    return None if node is None else compile_secret_node(node, ctx)
