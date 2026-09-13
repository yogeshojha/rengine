"""The drill-down token a count is a promise for."""

from __future__ import annotations

import re

_NEEDS_QUOTE = re.compile(r'[\s()"\[\]:=><~]')


def token(field: str, op: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    quoted = f'"{escaped}"' if _NEEDS_QUOTE.search(value) or not value else value
    return f"{field}{op}{quoted}"


group_token = token
