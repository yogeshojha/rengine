#!/usr/bin/env python3
"""Regenerate shared/definitions/data/port_registry.json from the IANA port registry.

The registry is public domain and slow-moving, so the generated file is committed
rather than fetched at build time. Run this when IANA publishes an update:

    python3 scripts/fetch_port_registry.py

IANA is the fallback vocabulary only. shared/definitions/ports.py:WELL_KNOWN stays
authoritative, because IANA still calls 9200 "wap-wsp" and 5601 "esmagent" while the
internet uses those ports for Elasticsearch and Kibana.
"""

from __future__ import annotations

import csv
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE = (
    "https://www.iana.org/assignments/service-names-port-numbers/"
    "service-names-port-numbers.csv"
)
TARGET = (
    Path(__file__).resolve().parents[1] / "shared/definitions/data/port_registry.json"
)
PROTOCOLS = ("tcp",)
MAX_DESCRIPTION = 120
UNASSIGNED = {"", "reserved", "unassigned", "de-registered", "deregistered"}

_ALNUM = re.compile(r"[^a-z0-9]")
# IANA appends its own registration housekeeping to 94 descriptions; it says nothing
# about the service
_HOUSEKEEPING = re.compile(
    r"\s*IANA assigned this well-formed service name as a replacement for.*$", re.I
)


def _same(a: str, b: str) -> bool:
    return _ALNUM.sub("", a.lower()) == _ALNUM.sub("", b.lower())


def build(raw: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in csv.DictReader(io.StringIO(raw)):
        if (row["Transport Protocol"] or "").strip().lower() not in PROTOCOLS:
            continue
        number = (row["Port Number"] or "").strip()
        name = (row["Service Name"] or "").strip().lower()
        description = _HOUSEKEEPING.sub(
            "", " ".join((row["Description"] or "").split())
        )
        if not number.isdigit() or not name or number in out:
            continue
        if description.lower() in UNASSIGNED or len(description) > MAX_DESCRIPTION:
            continue
        # a description that only restates the name carries nothing the UI cannot infer
        out[number] = [name] if _same(description, name) else [name, description]
    return out


def main() -> int:
    with urllib.request.urlopen(SOURCE, timeout=60) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    registry = build(raw)
    if len(registry) < 4000:  # noqa: PLR2004
        print(
            f"refusing to write a suspiciously small registry ({len(registry)} ports)"
        )
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(registry, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    described = sum(1 for entry in registry.values() if len(entry) > 1)
    print(f"{TARGET}: {len(registry)} ports, {described} with a description")
    return 0


if __name__ == "__main__":
    sys.exit(main())
