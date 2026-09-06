from __future__ import annotations

import fnmatch
import ipaddress
import re

# regex/glob metacharacters that signal an entry is a pattern, not a literal domain
_METACHARS = frozenset("*?^$()[]{}+|\\")


def looks_like_domain(pattern: str) -> bool:
    """A literal FQDN has a dot but no regex/glob metacharacters."""
    return "." in pattern and not any(c in _METACHARS for c in pattern)


# a quantified group whose body is itself quantified is the shape that backtracks
# catastrophically: (a+)+, (x*)*, ([a-z]+){2,}. Matching runs per discovered host,
# so one of these hangs a stage until the task time limit.
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


def _has_quantifier(body: str) -> bool:
    escaped = False
    for i, char in enumerate(body):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char in _QUANTIFIERS or (char == "{" and _quantified_at(body, i)):
            return True
    return False


def backtracks_badly(pattern: str) -> bool:
    """Whether a pattern repeats a group that already repeats, which can never match quickly."""
    stack: list[int] = []
    escaped = False
    for i, char in enumerate(pattern or ""):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
        elif char == "(":
            stack.append(i)
        elif char == ")" and stack:
            opened = stack.pop()
            if _quantified_at(pattern, i + 1) and _has_quantifier(
                pattern[opened + 1 : i]
            ):
                return True
    return False


def compile_pattern(pattern: str) -> re.Pattern[str]:
    """Compile an exclusion entry: regex if valid, else glob (handles *admin*)."""
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error:
        return re.compile(fnmatch.translate(pattern), re.IGNORECASE)


def matches_any(value: str, patterns: list[str]) -> bool:
    """True if value matches any exclusion pattern (keyword substring / wildcard / regex)."""
    for pattern in patterns or []:
        if pattern and compile_pattern(pattern).search(value):
            return True
    return False


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
            if compile_pattern(entry).search(value):
                return True
            continue
        if address.version == network.version and address in network:
            return True
    return False
