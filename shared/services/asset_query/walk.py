"""The AST walk every dimension shares: a compiler supplies its builders and its free text."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy import and_, false, or_, true

from shared.definitions.asset_query import Op, QueryRegistry

from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term
from .terms import negate

Builder = Callable[[Compare, Any], Any]
Builders = dict[str, Builder]
FlagBuilders = dict[str, Callable[[Any], Any]]
Walker = Callable[[Node | None, Any], Any]


def compare_with(builders: Builders, cmp: Compare, ctx: Any):
    """The predicate a field's builder returns, or a syntax error naming the field."""
    builder = builders.get(cmp.name)
    if builder is None:
        msg = f"Field {cmp.name!r} cannot be searched."
        raise QuerySyntaxError(msg, cmp.start, cmp.end)
    return builder(cmp, ctx)


def flag_builder(flags: FlagBuilders, known: Iterable[str]) -> Builder:
    """The `is:` builder: rows carrying any named flag, an unknown flag a syntax error.

    `known` is the dimension's documented flag list, quoted in the hint.
    """
    hint = f"Try one of: {', '.join(known)}"

    def build(cmp: Compare, ctx: Any):
        branches = []
        for raw in cmp.values:
            builder = flags.get(raw.lower())
            if builder is None:
                msg = f"Unknown flag {raw!r}."
                raise QuerySyntaxError(msg, cmp.start, cmp.end, hint)
            branches.append(builder(ctx))
        return or_(*branches)

    return build


def as_compare(term: Term, field: str) -> Compare:
    """A bare word read as a match on one free-text field."""
    return Compare(
        name=field,
        op=Op.MATCH,
        values=(term.value,),
        quoted=term.quoted,
        sub=None,
        start=term.start,
        end=term.end,
    )


def free_text_fields(registry: QueryRegistry) -> tuple[str, ...]:
    return tuple(spec.name for spec in registry.fields if spec.free_text)


def walker(
    registry: QueryRegistry,
    builders: Builders,
    *,
    term: Callable[[Term, Any], Any] | None = None,
    compare: Callable[[Compare, Any], Any] | None = None,
    fold_or: Callable[[Or, Any, Walker], Any] | None = None,
) -> Walker:
    """The `compile_<dimension>_query` a dimension exposes."""
    compare_fn = compare or (lambda cmp, ctx: compare_with(builders, cmp, ctx))

    def term_fn(node: Term, ctx: Any):
        branches = [
            compare_with(builders, as_compare(node, field), ctx)
            for field in free_text_fields(registry)
        ]
        return or_(*branches) if branches else false()

    read_term = term or term_fn

    def node_fn(node: Node, ctx: Any):
        if isinstance(node, Term):
            return read_term(node, ctx)
        if isinstance(node, Compare):
            return compare_fn(node, ctx)
        if isinstance(node, Not):
            return negate(node_fn(node.part, ctx))
        if isinstance(node, And):
            return and_(*[node_fn(p, ctx) for p in node.parts])
        if isinstance(node, Or):
            return (
                fold_or(node, ctx, node_fn)
                if fold_or is not None
                else or_(*[node_fn(p, ctx) for p in node.parts])
            )
        return true()

    def compile_query(node: Node | None, ctx: Any):
        return None if node is None else node_fn(node, ctx)

    return compile_query
