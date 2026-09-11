#!/usr/bin/env python3
"""Regenerate tools/data/content.txt from SecLists' web-content discovery list."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

SOURCE = (
    "https://raw.githubusercontent.com/danielmiessler/SecLists/master/"
    "Discovery/Web-Content/raft-{size}-{kind}.txt"
)
KINDS = ("directories", "files")
SIZES = ("small", "medium", "large")
OUTPUT = Path(__file__).resolve().parent.parent / "tools" / "data" / "content.txt"

_WORD = re.compile(r"^[A-Za-z0-9._~!$&'()*+,;=:@%-]{1,100}$")


def fetch(size: str, kind: str) -> list[str]:
    url = SOURCE.format(size=size, kind=kind)
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
        body = response.read().decode("utf-8", errors="replace")
    out: list[str] = []
    for raw in body.splitlines():
        word = raw.strip().lstrip("/")
        if word and not word.startswith("#") and _WORD.match(word):
            out.append(word)
    return out


def merge(size: str) -> list[str]:
    """Directories before files at each rank."""
    seen: set[str] = set()
    ranked: list[str] = []
    columns = [fetch(size, kind) for kind in KINDS]
    for row in range(max(len(c) for c in columns)):
        for column in columns:
            if row >= len(column):
                continue
            word = column[row]
            if word.lower() in seen:
                continue
            seen.add(word.lower())
            ranked.append(word)
    return ranked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", choices=SIZES, default="small")
    parser.add_argument("--limit", type=int, default=6000)
    args = parser.parse_args()

    try:
        words = merge(args.size)
    except OSError as e:
        print(f"could not fetch the wordlist: {e}", file=sys.stderr)
        return 1

    kept = words[: args.limit]
    OUTPUT.write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"wrote {len(kept):,} words to {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
