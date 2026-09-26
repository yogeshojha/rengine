"""wafw00f output, reduced to the firewall each URL sits behind."""

from __future__ import annotations

import json
import re

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_ARRAY_RE = re.compile(r"\[\s*\{.*\}\s*\]", re.DOTALL)
# wafw00f's names for "no firewall identified"
_NO_FIREWALL = frozenset({"none", "generic"})
MAX_NAME = 100


def extract_json_array(raw: str) -> list:
    """The JSON array wafw00f writes, found among its banner and colour codes."""
    match = _ARRAY_RE.search(_ANSI_RE.sub("", raw))
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def parse_detections(raw: str) -> dict[str, str]:
    """{url: firewall} for every URL wafw00f named a firewall for."""
    out: dict[str, str] = {}
    for rec in extract_json_array(raw):
        url = rec.get("url")
        name = rec.get("firewall")
        if url and rec.get("detected") and name and name.lower() not in _NO_FIREWALL:
            out[url] = name[:MAX_NAME]
    return out
