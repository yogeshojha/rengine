from __future__ import annotations

import re
from dataclasses import dataclass

from shared.definitions.asset_query import (
    CANONICAL,
    FIELDS_BY_NAME,
    MAX_FREE_TERMS,
    MAX_QUERY_LENGTH,
    MAX_QUERY_NODES,
    OPS_BY_TYPE,
    Op,
)

from .ast import And, Compare, Node, Not, Or, QuerySyntaxError, Term

_OPS = ("!=", ">=", "<=", "!~", ":", "=", ">", "<", "~")
_CONNECTORS = {"and": "AND", "&&": "AND", "or": "OR", "||": "OR", "not": "NOT"}
_MAX_REGEX = 200
_QUOTE_PAIR = 2
_DYNAMIC_PARENT = "header"


@dataclass(frozen=True)
class Token:
    kind: str
    start: int
    end: int
    text: str = ""
    field: str = ""
    op: Op = Op.MATCH
    values: tuple[str, ...] = ()
    quoted: bool = False
    sub: str | None = None


def _resolve(name: str) -> tuple[str, str | None] | None:
    key = name.lower()
    if key in CANONICAL:
        return CANONICAL[key], None
    parent, _, sub = key.partition(".")
    if sub and CANONICAL.get(parent) == _DYNAMIC_PARENT:
        return _DYNAMIC_PARENT, sub
    return None


def _split_values(raw: str, start: int) -> tuple[list[str], bool]:
    if raw.startswith("[") and raw.endswith("]"):
        listed = [v.strip() for v in _split_list(raw[1:-1]) if v.strip()]
        if not listed:
            msg = "This list is empty."
            raise QuerySyntaxError(msg, start, start + 1, "Name at least one value.")
        return listed, False
    if len(raw) >= _QUOTE_PAIR and raw.startswith('"') and raw.endswith('"'):
        return [_unescape(raw[1:-1])], True
    if not raw:
        msg = "This filter needs a value."
        hint = "Quote the value if it contains a space or a bracket."
        raise QuerySyntaxError(msg, start, start + 1, hint)
    return [raw], False


def _split_list(raw: str) -> list[str]:
    out: list[str] = []
    buf: list[str] = []
    quoted = False
    i = 0
    while i < len(raw):
        c = raw[i]
        if quoted:
            if c == "\\" and i + 1 < len(raw):
                buf.append(raw[i + 1])
                i += 2
                continue
            if c == '"':
                quoted = False
            else:
                buf.append(c)
        elif c == '"':
            quoted = True
        elif c == ",":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return out


def _unescape(raw: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(raw):
        if raw[i] == "\\" and i + 1 < len(raw):
            out.append(raw[i + 1])
            i += 2
            continue
        out.append(raw[i])
        i += 1
    return "".join(out)


class _Scanner:
    def __init__(self, source: str):
        self.s = source
        self.n = len(source)
        self.i = 0

    def skip_space(self) -> None:
        while self.i < self.n and self.s[self.i].isspace():
            self.i += 1

    def chunk(self) -> tuple[str, int, int]:
        start = self.i
        quoted = False
        depth = 0
        while self.i < self.n:
            c = self.s[self.i]
            if quoted:
                if c == "\\" and self.i + 1 < self.n:
                    self.i += 2
                    continue
                if c == '"':
                    quoted = False
                self.i += 1
                continue
            if c == '"':
                quoted = True
                self.i += 1
                continue
            if c == "[":
                depth += 1
            elif c == "]":
                depth = max(0, depth - 1)
            elif depth == 0 and (c.isspace() or c in "()"):
                break
            self.i += 1
        if quoted:
            msg = "This quote is never closed."
            raise QuerySyntaxError(msg, start, self.n, "Close it with a quote.")
        if depth:
            msg = "This list is never closed."
            raise QuerySyntaxError(msg, start, self.n, "Close it with ].")
        return self.s[start : self.i], start, self.i

    def peek_op(self) -> tuple[str, int, int] | None:
        save = self.i
        self.skip_space()
        for op in _OPS:
            if self.s.startswith(op, self.i):
                start = self.i
                self.i += len(op)
                return op, start, self.i
        self.i = save
        return None


def tokenize(source: str) -> list[Token]:
    scanner = _Scanner(source)
    tokens: list[Token] = []
    while True:
        scanner.skip_space()
        if scanner.i >= scanner.n:
            return tokens
        c = scanner.s[scanner.i]
        if c in "()":
            tokens.append(
                Token(
                    "LPAREN" if c == "(" else "RPAREN", scanner.i, scanner.i + 1, text=c
                )
            )
            scanner.i += 1
            continue
        text, start, end = scanner.chunk()
        if not text:
            scanner.i += 1
            continue
        lowered = text.lower()
        if lowered in _CONNECTORS:
            tokens.append(Token(_CONNECTORS[lowered], start, end, text=text))
            continue
        if len(text) > 1 and text[0] in "-!" and not text.startswith(("!=", "!~")):
            tokens.append(Token("NOT", start, start + 1, text=text[0]))
            scanner.i = start + 1
            continue
        tokens.append(_field_or_term(scanner, text, start, end))


def _field_or_term(scanner: _Scanner, text: str, start: int, end: int) -> Token:
    split = _find_operator(text)
    if split is not None:
        name, op_text, rest = split
        if not rest:
            scanner.skip_space()
            rest, _, end = scanner.chunk()
        return _compare(name, op_text, rest, start, end)
    if _resolve(text) is not None:
        found = scanner.peek_op()
        if found is not None:
            op_text, _, _ = found
            scanner.skip_space()
            rest, _, end = scanner.chunk()
            return _compare(text, op_text, rest, start, end)
    if len(text) >= _QUOTE_PAIR and text.startswith('"') and text.endswith('"'):
        return Token("TERM", start, end, text=_unescape(text[1:-1]), quoted=True)
    return Token("TERM", start, end, text=text)


def _find_operator(text: str) -> tuple[str, str, str] | None:
    for i in range(1, len(text)):
        for op in _OPS:
            if not text.startswith(op, i):
                continue
            if _resolve(text[:i]) is None:
                continue
            return text[:i], op, text[i + len(op) :]
    return None


def _compare(name: str, op_text: str, raw: str, start: int, end: int) -> Token:
    resolved = _resolve(name)
    if resolved is None:
        msg = f"Unknown field {name!r}."
        hint = "Press ? for the full field list."
        raise QuerySyntaxError(msg, start, start + len(name), hint)
    canonical, sub = resolved
    op = Op(op_text)
    if op is Op.MATCH:
        for candidate in ("!=", ">=", "<=", ">", "<", "!~", "~", "="):
            if raw.startswith(candidate):
                op = Op(candidate)
                raw = raw[len(candidate) :].lstrip()
                break
    values, quoted = _split_values(raw, end)
    spec = FIELDS_BY_NAME[canonical]
    if op not in OPS_BY_TYPE[spec.type]:
        allowed = " ".join(o.value for o in OPS_BY_TYPE[spec.type])
        msg = f"{canonical} does not support {op.value}."
        raise QuerySyntaxError(msg, start, end, f"It accepts: {allowed}")
    if op in (Op.RE, Op.NRE):
        if any(len(v) > _MAX_REGEX for v in values):
            msg = "That regular expression is too long."
            raise QuerySyntaxError(msg, start, end)
        for value in values:
            try:
                re.compile(value)
            except re.error as exc:
                msg = f"{value!r} is not a valid regular expression."
                raise QuerySyntaxError(msg, start, end, str(exc)) from exc
    return Token(
        "CMP",
        start,
        end,
        field=canonical,
        op=op,
        values=tuple(values),
        quoted=quoted,
        sub=sub,
        text=name,
    )


class _Parser:
    def __init__(self, tokens: list[Token], source: str):
        self.tokens = tokens
        self.source = source
        self.i = 0
        self.nodes = 0
        self.terms = 0

    def at(self, kind: str) -> bool:
        return self.i < len(self.tokens) and self.tokens[self.i].kind == kind

    def count(self) -> None:
        self.nodes += 1
        if self.nodes > MAX_QUERY_NODES:
            msg = "That query has too many parts."
            raise QuerySyntaxError(msg, 0, len(self.source))

    def parse(self) -> Node | None:
        if not self.tokens:
            return None
        node = self.or_expr()
        if self.i < len(self.tokens):
            token = self.tokens[self.i]
            msg = f"Unexpected {token.text or token.kind.lower()!r}."
            raise QuerySyntaxError(msg, token.start, token.end)
        return node

    def or_expr(self) -> Node:
        parts = [self.and_expr()]
        while self.at("OR"):
            self.i += 1
            parts.append(self.and_expr())
        return parts[0] if len(parts) == 1 else Or(tuple(parts))

    def and_expr(self) -> Node:
        parts = [self.unary()]
        while True:
            if self.at("AND"):
                self.i += 1
                parts.append(self.unary())
                continue
            if self.i < len(self.tokens) and self.tokens[self.i].kind in (
                "TERM",
                "CMP",
                "NOT",
                "LPAREN",
            ):
                parts.append(self.unary())
                continue
            break
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def unary(self) -> Node:
        if self.at("NOT"):
            self.i += 1
            return Not(self.unary())
        return self.primary()

    def primary(self) -> Node:
        self.count()
        if self.at("LPAREN"):
            open_token = self.tokens[self.i]
            self.i += 1
            node = self.or_expr()
            if not self.at("RPAREN"):
                msg = "This group is never closed."
                hint = "Close it with )."
                raise QuerySyntaxError(msg, open_token.start, len(self.source), hint)
            self.i += 1
            return node
        if self.i >= len(self.tokens):
            msg = "The query ends early."
            raise QuerySyntaxError(msg, len(self.source), len(self.source))
        token = self.tokens[self.i]
        self.i += 1
        if token.kind == "TERM":
            self.terms += 1
            if self.terms > MAX_FREE_TERMS:
                msg = "That is too many words to search at once."
                hint = f"Use at most {MAX_FREE_TERMS}, or narrow with a field."
                raise QuerySyntaxError(msg, token.start, token.end, hint)
            return Term(token.text, token.quoted, token.start, token.end)
        if token.kind == "CMP":
            return Compare(
                name=token.field,
                op=token.op,
                values=token.values,
                quoted=token.quoted,
                sub=token.sub,
                start=token.start,
                end=token.end,
                raw_name=token.text,
            )
        msg = f"{token.text or token.kind.lower()!r} needs something to act on."
        raise QuerySyntaxError(msg, token.start, token.end)


def parse_query(source: str | None) -> Node | None:
    if not source or not source.strip():
        return None
    if len(source) > MAX_QUERY_LENGTH:
        msg = "That query is too long."
        raise QuerySyntaxError(msg, 0, len(source))
    return _Parser(tokenize(source), source).parse()
