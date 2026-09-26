"""Read the literals a frontend config module declares, for drift tests against shared/definitions.

The frontend keeps copies of backend vocabularies in ``frontend/src/lib/config/*.ts``.
This reader understands the subset of TypeScript those copies use: ``export enum``,
``export const X = { ... } as const``, and ``export const X[: T] = <literal>`` where the
literal is an object, an array, ``new Set([...])``, a string, a template or a number.
Computed keys and values written as ``Enum.MEMBER`` resolve through the enums and
const objects of the same file; anything else (an icon, a spread, a call) comes back as
a ``Ref`` so a test can skip it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# the test container mounts frontend/src/lib/config here; a local run reads the tree
_MOUNTED = Path("/app/frontend-config")
_TREE = Path(__file__).resolve().parents[2] / "frontend" / "src" / "lib" / "config"
CONFIG_DIR = _MOUNTED if _MOUNTED.is_dir() else _TREE

_TOKEN = re.compile(
    r"""
    (?P<space>\s+|//[^\n]*|/\*.*?\*/)
    |(?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
    |(?P<template>`(?:[^`\\]|\\.)*`)
    |(?P<number>-?\d[\d_]*(?:\.\d+)?)
    |(?P<spread>\.\.\.)
    |(?P<name>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)
    |(?P<punct>[{}\[\](),:;<>=?|&!.+*/-])
    """,
    re.S | re.X,
)
_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "0": "\0"}


@dataclass(frozen=True)
class Ref:
    """A value the reader does not evaluate: an import, an icon, a spread, a call."""

    name: str


def _unquote(raw: str) -> str:
    return re.sub(r"\\(.)", lambda m: _ESCAPES.get(m.group(1), m.group(1)), raw[1:-1])


def _scalar(kind: str, text: str) -> str | int | float | Ref:
    if kind == "string":
        return _unquote(text)
    if kind == "template":
        return text[1:-1]
    if kind == "number":
        number = text.replace("_", "")
        return float(number) if "." in number else int(number)
    return Ref(text)


def _tokens(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    pos = 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            out.append(("punct", text[pos]))
            pos += 1
            continue
        pos = m.end()
        kind = m.lastgroup or "punct"
        if kind != "space":
            out.append((kind, m.group(kind)))
    return out


class _Parser:
    def __init__(self, tokens: list[tuple[str, str]], names: dict[str, str]) -> None:
        self.tokens = tokens
        self.names = names
        self.pos = 0

    def peek(self, offset: int = 0) -> tuple[str, str]:
        i = self.pos + offset
        return self.tokens[i] if i < len(self.tokens) else ("end", "")

    def take(self, value: str | None = None) -> tuple[str, str]:
        token = self.peek()
        if value is not None and token[1] != value:
            msg = f"expected {value!r}, found {token[1]!r}"
            raise ValueError(msg)
        self.pos += 1
        return token

    def resolve(self, name: str) -> str | Ref:
        return self.names.get(name, Ref(name))

    def value(self):
        kind, text = self.peek()
        if text == "{":
            return self.obj()
        if text == "[":
            return self.array()
        if kind == "name" and text == "new":
            return self.construct()
        self.take()
        if kind == "name":
            return self.name(text)
        return _scalar(kind, text)

    def construct(self) -> set | Ref:
        """``new Set([...])``; any other constructor is left unevaluated."""
        self.take("new")
        ctor = self.take()[1]
        self.take("(")
        inner = self.value() if self.peek()[1] != ")" else []
        self.take(")")
        return set(inner) if ctor == "Set" and isinstance(inner, list) else Ref(ctor)

    def name(self, text: str) -> str | Ref:
        if self.peek()[1] == "(":
            self.skip_group()
            return Ref(text)
        return self.resolve(text)

    def skip_group(self) -> None:
        opener = self.take()[1]
        closer = {"(": ")", "[": "]", "{": "}"}[opener]
        depth = 1
        while depth:
            text = self.take()[1]
            if text == opener:
                depth += 1
            elif text == closer:
                depth -= 1

    def key(self):
        kind, text = self.take()
        if text == "[":
            inner = self.value()
            self.take("]")
            return inner
        if kind == "string":
            return _unquote(text)
        return text

    def obj(self) -> dict:
        self.take("{")
        out: dict = {}
        while self.peek()[1] != "}":
            if self.peek()[0] == "spread":
                self.take()
                out.setdefault(Ref("..."), []).append(self.value())
            else:
                key = self.key()
                self.take(":")
                out[key] = self.value()
            if self.peek()[1] == ",":
                self.take()
        self.take("}")
        return out

    def array(self) -> list:
        self.take("[")
        out: list = []
        while self.peek()[1] != "]":
            if self.peek()[0] == "spread":
                self.take()
                spread = self.value()
                out.append(
                    Ref(f"...{spread.name if isinstance(spread, Ref) else spread}")
                )
            else:
                out.append(self.value())
            if self.peek()[1] == ",":
                self.take()
        self.take("]")
        return out


class Mirror:
    """One frontend config module, read for its exported literals."""

    def __init__(self, filename: str) -> None:
        self.path = CONFIG_DIR / filename
        self.text = self.path.read_text()
        self.names: dict[str, str] = dict(
            re.findall(r"export const (\w+)(?:: string)? = '([^']*)';", self.text)
        )
        for name, members in self.enums().items():
            for member, value in members.items():
                self.names[f"{name}.{member}"] = value

    def enums(self) -> dict[str, dict[str, str]]:
        """``export enum X { A = 'a' }`` and ``export const X = { A: 'a' } as const``."""
        found: dict[str, dict[str, str]] = {}
        for name, body in re.findall(r"export enum (\w+) \{(.*?)\}", self.text, re.S):
            found[name] = dict(re.findall(r"(\w+) = '([^']*)'", body))
        for name, body in re.findall(
            r"export const (\w+) = \{([^{}]*)\} as const;", self.text, re.S
        ):
            members = dict(re.findall(r"(\w+): '([^']*)'", body))
            if members:
                found[name] = members
        return found

    def enum(self, name: str) -> dict[str, str]:
        members = self.enums().get(name)
        assert members, f"{name} is missing from {self.path.name}"
        return members

    def values(self, name: str) -> set[str]:
        return set(self.enum(name).values())

    def const(self, name: str):
        found = re.search(rf"^(?:export )?const {name}\b", self.text, re.M)
        assert found, f"{name} is missing from {self.path.name}"
        tokens = _tokens(self.text[found.end() :])
        depth = 0
        for i, (_, text) in enumerate(tokens):
            if text in "<([{":
                depth += 1
            elif text in ">)]}":
                depth -= 1
            elif text == "=" and depth == 0:
                return _Parser(tokens[i + 1 :], self.names).value()
        msg = f"{name} has no initialiser in {self.path.name}"
        raise AssertionError(msg)

    def labels(self, name: str) -> dict[str, str]:
        """An object literal of plain entries, with spreads and unresolved keys dropped."""
        return {
            k: v
            for k, v in self.const(name).items()
            if isinstance(k, str) and isinstance(v, str)
        }


def spreads(value: dict) -> list:
    """What an object literal spreads into itself, as ``Ref`` names."""
    return value.get(Ref("..."), [])
