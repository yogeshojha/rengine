from __future__ import annotations

import fnmatch
import ipaddress
import re
from functools import lru_cache
from re import _parser

import regex

from shared.logging import get_logger

logger = get_logger(__name__)

_METACHARS = frozenset("*?^$()[]{}+|\\")
_GROUP_DIGITS = frozenset("123456789")

MATCH_SECONDS = 0.1
MAX_TIMEOUTS = 5
MAX_EXPANSION = 10_000

NESTED_REPEAT = "nests a repeated group"
REPEATED_ALTERNATION = "repeats a group with alternatives"
BACKREFERENCE = "uses a backreference"
TOO_MANY_REPEATS = "repeats too many times"
TOO_DEEP = "nests too many groups"

_REPEATS = frozenset(
    {_parser.MAX_REPEAT, _parser.MIN_REPEAT, _parser.POSSESSIVE_REPEAT}
)


def looks_like_domain(pattern: str) -> bool:
    """A literal FQDN has a dot but no regex/glob metacharacters."""
    return "." in pattern and not any(c in _METACHARS for c in pattern)


_QUANTIFIERS = "+*"


def _quantified_at(pattern: str, index: int) -> bool:
    """Whether the token ending just before index carries a repeat."""
    if index >= len(pattern):
        return False
    char = pattern[index]
    if char in _QUANTIFIERS:
        return True
    if char != "{":
        return False
    close = pattern.find("}", index)
    return close != -1 and pattern[index + 1 : close].rstrip().endswith(",")


def _class_end(pattern: str, index: int) -> int:
    """Index of the bracket that closes the character class opened at index."""
    i = index + 1
    if i < len(pattern) and pattern[i] == "^":
        i += 1
    if i < len(pattern) and pattern[i] == "]":
        i += 1
    while i < len(pattern):
        if pattern[i] == "\\":
            i += 2
            continue
        if pattern[i] == "]":
            return i
        i += 1
    return len(pattern)


def _shape_hazard(pattern: str) -> str | None:
    """A construct that backtracks without bound: repeated nesting, alternation or a backreference."""
    stack = [[False, False]]
    i = 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\":
            if pattern[i + 1 : i + 2] in _GROUP_DIGITS:
                return BACKREFERENCE
            i += 2
            continue
        if char == "[":
            i = _class_end(pattern, i) + 1
            continue
        if char == "(":
            if pattern.startswith(("(?P=", "(?("), i):
                return BACKREFERENCE
            stack.append([False, False])
        elif char == ")" and len(stack) > 1:
            repeats, branches = stack.pop()
            if _quantified_at(pattern, i + 1):
                if repeats:
                    return NESTED_REPEAT
                if branches:
                    return REPEATED_ALTERNATION
            stack[-1][0] = stack[-1][0] or repeats
            stack[-1][1] = stack[-1][1] or branches
        elif char == "|":
            stack[-1][1] = True
        elif char in _QUANTIFIERS or (char == "{" and _quantified_at(pattern, i)):
            stack[-1][0] = True
        i += 1
    return None


def _children(value) -> list:
    if isinstance(value, _parser.SubPattern):
        return [value]
    if isinstance(value, list | tuple):
        return [child for item in value for child in _children(item)]
    return []


def _expansion(items) -> int:
    """How many nodes the compiled form unrolls to, stopping past MAX_EXPANSION."""
    total = 0
    for op, av in items:
        weight = max(av[0], 1) if op in _REPEATS else 1
        total += weight * (sum(_expansion(child) for child in _children(av)) or 1)
        if total > MAX_EXPANSION:
            break
    return total


def _parsed(pattern: str) -> tuple[str, _parser.SubPattern]:
    """The source an exclusion entry compiles from: itself if a valid regex, else its glob."""
    try:
        return pattern, _parser.parse(pattern, re.IGNORECASE)
    except re.error:
        source = fnmatch.translate(pattern)
        return source, _parser.parse(source, re.IGNORECASE)


def pattern_hazard(pattern: str) -> str | None:
    """Why an exclusion entry is refused, or None."""
    if not pattern:
        return None
    try:
        source, tree = _parsed(pattern)
        if _expansion(tree) > MAX_EXPANSION:
            return TOO_MANY_REPEATS
    except RecursionError:
        return TOO_DEEP
    return _shape_hazard(pattern) if source == pattern else None


class Exclusion:
    """A compiled exclusion entry whose match is bounded in time."""

    __slots__ = ("compiled", "pattern", "timeouts")

    def __init__(self, pattern: str, compiled: regex.Pattern | None):
        self.pattern = pattern
        self.compiled = compiled
        self.timeouts = 0

    def hits(self, value: str) -> bool:
        """True when value matches, or when the entry cannot be evaluated."""
        if self.compiled is None or self.timeouts >= MAX_TIMEOUTS:
            return True
        try:
            found = self.compiled.search(value, timeout=MATCH_SECONDS, concurrent=True)
        except TimeoutError:
            self.timeouts += 1
            logger.warning(
                "scope pattern timed out", pattern=self.pattern, timeouts=self.timeouts
            )
            return True
        return found is not None


def _compiled(pattern: str) -> regex.Pattern | None:
    try:
        source, tree = _parsed(pattern)
        if _expansion(tree) > MAX_EXPANSION:
            return None
        try:
            return regex.compile(source, regex.IGNORECASE)
        except regex.error:
            return regex.compile(fnmatch.translate(pattern), regex.IGNORECASE)
    except RecursionError:
        return None


@lru_cache(maxsize=4096)
def compile_pattern(pattern: str) -> Exclusion:
    """Compile an exclusion entry: regex if valid, else glob (handles *admin*)."""
    compiled = _compiled(pattern)
    if compiled is None:
        logger.warning("scope pattern not evaluated", pattern=pattern)
    return Exclusion(pattern, compiled)


def matches_any(value: str, patterns: list[str]) -> bool:
    """True if value matches any exclusion pattern (keyword substring / wildcard / regex)."""
    return any(compile_pattern(p).hits(value) for p in patterns or [] if p)


def ip_excluded(value: str, patterns: list[str]) -> bool:
    """True if an address falls inside any exclusion entry (CIDR, literal, or pattern)."""
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return matches_any(value, patterns)
    for pattern in patterns or []:
        entry = (pattern or "").strip()
        if not entry:
            continue
        try:
            network = ipaddress.ip_network(entry, strict=False)
        except ValueError:
            if compile_pattern(entry).hits(value):
                return True
            continue
        if address.version == network.version and address in network:
            return True
    return False


def host_excluded(
    host: str, excluded_hosts: list[str], excluded_ips: list[str]
) -> bool:
    """True if a URL host matches a host exclusion or is an address inside an excluded range."""
    if matches_any(host, excluded_hosts):
        return True
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip_excluded(host, excluded_ips)
