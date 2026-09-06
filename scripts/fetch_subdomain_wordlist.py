#!/usr/bin/env python3
"""Regenerate tools/data/subdomains.txt from SecLists' DNS discovery list.

The list is MIT-licensed and slow-moving, so the generated file is committed rather
than fetched at build time — a scan on a box with no egress still gets a wordlist.
Run this when you want a newer cut:

    python3 scripts/fetch_subdomain_wordlist.py [--size 5000]

Names are ranked by how often they appeared in a real DNS corpus, so the order is the
budget: the resolver walks the file top to bottom and a smaller wordlist is simply the
first N lines. Keep it that way.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

SOURCE = (
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/"
    "Discovery/DNS/subdomains-top1million-{size}.txt"
)
SIZES = (5000, 20000, 110000)
OUTPUT = Path(__file__).resolve().parent.parent / "tools" / "data" / "subdomains.txt"

# one DNS label: what dnsx will prefix onto the apex, nothing else
_LABEL = re.compile(r"^[a-z0-9_](?:[a-z0-9_-]{0,61}[a-z0-9_])?$")


def fetch(size: int) -> list[str]:
    with urllib.request.urlopen(SOURCE.format(size=size), timeout=60) as response:  # noqa: S310
        body = response.read().decode("utf-8", errors="replace")
    seen: set[str] = set()
    labels: list[str] = []
    for raw in body.splitlines():
        label = raw.strip().lower()
        if not label or label in seen or not _LABEL.match(label):
            continue
        seen.add(label)
        labels.append(label)
    return labels


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--size", type=int, default=5000, choices=SIZES)
    args = parser.parse_args()

    labels = fetch(args.size)
    if len(labels) < args.size // 2:
        print(f"only {len(labels)} usable labels, refusing to write", file=sys.stderr)
        return 1
    OUTPUT.write_text("\n".join(labels) + "\n")
    print(f"wrote {OUTPUT} ({len(labels)} labels)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
