"""A block's query as the clauses a person reads."""

from __future__ import annotations

from mcp.dimensions import Dimension
from shared.definitions.ask import ReadKind
from shared.models.ask import ReadToken
from shared.services.asset_query import QuerySyntaxError
from shared.services.asset_query.parser import tokenize

FLAG_FIELDS = frozenset({"is"})
MATCH_OP = ":"
MAX_TOKENS = 12


def _flags(dim: Dimension, token, negated: bool) -> list[ReadToken]:
    out: list[ReadToken] = []
    for i, value in enumerate(token.values):
        if i:
            out.append(ReadToken(kind=ReadKind.OR.value, text="or"))
        out.append(
            ReadToken(
                kind=ReadKind.FLAG.value,
                text=dim.registry.flags.get(value, value),
                field=f"{token.field}:{value}",
                negated=negated,
            )
        )
    return out


def reading(dim: Dimension, query: str | None) -> list[ReadToken]:
    if not query:
        return []
    try:
        tokens = tokenize(query, dim.registry)
    except QuerySyntaxError:
        return []
    fields = dim.registry.by_name
    out: list[ReadToken] = []
    negated = False
    for token in tokens:
        if token.kind == "NOT":
            negated = True
            continue
        if token.kind == "OR":
            out.append(ReadToken(kind=ReadKind.OR.value, text="or"))
        elif token.kind == "LPAREN":
            out.append(ReadToken(kind=ReadKind.OPEN.value, text="(", negated=negated))
        elif token.kind == "RPAREN":
            out.append(ReadToken(kind=ReadKind.CLOSE.value, text=")"))
        elif token.kind == "CMP" and token.field in FLAG_FIELDS:
            out.extend(_flags(dim, token, negated))
        elif token.kind == "CMP":
            spec = fields.get(token.field)
            op = token.op.value
            out.append(
                ReadToken(
                    kind=ReadKind.FIELD.value,
                    text=", ".join(token.values),
                    field=token.field,
                    op=None if op == MATCH_OP else op,
                    negated=negated,
                    hint=spec.description if spec else None,
                )
            )
        elif token.kind == "TERM":
            out.append(
                ReadToken(kind=ReadKind.TEXT.value, text=token.text, negated=negated)
            )
        negated = False
    if len(out) <= MAX_TOKENS:
        return out
    kept = out[:MAX_TOKENS]
    depth = sum(
        (t.kind == ReadKind.OPEN.value) - (t.kind == ReadKind.CLOSE.value) for t in kept
    )
    closing = [ReadToken(kind=ReadKind.CLOSE.value, text=")")] * max(depth, 0)
    return [*kept, ReadToken(kind=ReadKind.MORE.value, text="…"), *closing]


def fields_of(dim: Dimension, query: str | None) -> set[str]:
    """The fields and flags a query names."""
    if not query:
        return set()
    try:
        tokens = tokenize(query, dim.registry)
    except QuerySyntaxError:
        return set()
    out: set[str] = set()
    for token in tokens:
        if token.kind != "CMP":
            continue
        if token.field in FLAG_FIELDS:
            out.update(f"{token.field}:{v}" for v in token.values)
        else:
            out.add(token.field)
    return out


def joined(query: str | None, clause: str) -> str:
    return f"({query}) and {clause}" if query else clause
