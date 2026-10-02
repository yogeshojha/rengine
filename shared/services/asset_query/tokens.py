from __future__ import annotations

import re

_NEEDS_QUOTE = re.compile(r'[\s()"\[\]:=><~]')


def _escaped(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def token(field: str, op: str, value: str) -> str:
    quoted = _escaped(value) if _NEEDS_QUOTE.search(value) or not value else value
    return f"{field}{op}{quoted}"


def list_token(field: str, values: list[str]) -> str:
    items = [
        _escaped(v) if _NEEDS_QUOTE.search(v) or "," in v or not v else v
        for v in values
    ]
    return f"{field}:[{','.join(items)}]"
