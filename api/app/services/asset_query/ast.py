from __future__ import annotations

from dataclasses import dataclass, field

from shared.definitions.asset_query import Op


class QuerySyntaxError(Exception):
    def __init__(self, message: str, start: int, end: int, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint
        self.start = start
        self.end = end


@dataclass(frozen=True)
class Term:
    value: str
    quoted: bool
    start: int
    end: int


@dataclass(frozen=True)
class Compare:
    name: str
    op: Op
    values: tuple[str, ...]
    quoted: bool
    sub: str | None
    start: int
    end: int
    raw_name: str = ""


@dataclass(frozen=True)
class Not:
    part: Node


@dataclass(frozen=True)
class And:
    parts: tuple[Node, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Or:
    parts: tuple[Node, ...] = field(default_factory=tuple)


Node = Term | Compare | Not | And | Or


def walk(node: Node, negated: bool = False):
    yield node, negated
    if isinstance(node, Not):
        yield from walk(node.part, not negated)
    elif isinstance(node, And | Or):
        for part in node.parts:
            yield from walk(part, negated)


def positive_terms(node: Node | None) -> list[Term]:
    if node is None:
        return []
    seen: dict[str, Term] = {}
    for item, negated in walk(node):
        if isinstance(item, Term) and not negated:
            seen.setdefault(item.value.lower(), item)
    return list(seen.values())


def positive_compares(node: Node | None) -> list[Compare]:
    if node is None:
        return []
    out: list[Compare] = []
    seen: set[tuple[str, str]] = set()
    for item, negated in walk(node):
        if not isinstance(item, Compare) or negated:
            continue
        if item.op not in (Op.MATCH, Op.EQ):
            continue
        key = (item.name, "\x00".join(item.values))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
