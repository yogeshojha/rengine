from __future__ import annotations

import fnmatch
import re

# regex/glob metacharacters that signal an entry is a pattern, not a literal domain
_METACHARS = frozenset("*?^$()[]{}+|\\")


def looks_like_domain(pattern: str) -> bool:
    """A literal FQDN has a dot but no regex/glob metacharacters."""
    return "." in pattern and not any(c in _METACHARS for c in pattern)


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
