#!/usr/bin/env python3
"""Regenerate shared/definitions/data/public_suffixes.json from the Public Suffix List."""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

SOURCE = "https://publicsuffix.org/list/public_suffix_list.dat"
TARGET = (
    Path(__file__).resolve().parents[1] / "shared/definitions/data/public_suffixes.json"
)
BEGIN = "===BEGIN ICANN DOMAINS==="
END = "===END ICANN DOMAINS==="
MIN_RULES = 5000


def build(raw: str) -> dict[str, list[str]]:
    suffixes: set[str] = set()
    wildcards: set[str] = set()
    exceptions: set[str] = set()
    tlds: set[str] = set()
    inside = False
    for line in raw.splitlines():
        if BEGIN in line:
            inside = True
            continue
        if END in line:
            break
        rule = line.strip().split()[0] if line.strip() else ""
        if not inside or not rule or rule.startswith("//"):
            continue
        rule = rule.encode("idna").decode("ascii") if not rule.isascii() else rule
        rule = rule.lower()
        tlds.add(rule.rsplit(".", 1)[-1])
        if rule.startswith("*."):
            wildcards.add(rule[2:])
        elif rule.startswith("!"):
            exceptions.add(rule[1:])
        elif "." in rule:
            suffixes.add(rule)
    return {
        "suffixes": sorted(suffixes),
        "wildcards": sorted(wildcards),
        "exceptions": sorted(exceptions),
        "tlds": sorted(tlds),
    }


def main() -> int:
    with urllib.request.urlopen(SOURCE, timeout=60) as response:  # noqa: S310
        raw = response.read().decode("utf-8")
    data = build(raw)
    if len(data["suffixes"]) < MIN_RULES:
        print(
            f"refusing to write only {len(data['suffixes'])} suffixes",
            file=sys.stderr,
        )
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(data, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        f"{TARGET}: {len(data['suffixes'])} suffixes, "
        f"{len(data['wildcards'])} wildcards, {len(data['exceptions'])} exceptions, "
        f"{len(data['tlds'])} tlds"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
