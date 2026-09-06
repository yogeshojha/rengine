#!/usr/bin/env python3
"""Vendor the report fonts. Run on a checkout; the files are committed so an offline box still renders."""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "reports" / "assets" / "fonts"
API = "https://fonts.googleapis.com/css2"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

# a body face carries the scripts a real estate is named in; display and mono stay latin
WIDE = "latin,latin-ext,greek,cyrillic"
LATIN = "latin,latin-ext"
MONO = "latin"

FAMILIES: dict[str, tuple[str, tuple[int, ...], bool, str]] = {
    "inter": ("Inter", (400, 500, 600, 700), False, WIDE),
    "space-grotesk": ("Space Grotesk", (400, 500, 700), False, LATIN),
    "ibm-plex-sans": ("IBM Plex Sans", (400, 600, 700), True, WIDE),
    "source-serif": ("Source Serif 4", (400, 600, 700), True, WIDE),
    "jetbrains-mono": ("JetBrains Mono", (400, 700), False, MONO),
    "ibm-plex-mono": ("IBM Plex Mono", (400, 600), False, MONO),
}

FACE_RE = re.compile(r"@font-face\s*\{(.*?)\}", re.S)


def _get(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": UA})  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return response.read().decode("utf-8")


def _download(url: str, path: Path) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": UA})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        data = response.read()
    path.write_bytes(data)
    return len(data)


def _spec(name: str, weights: tuple[int, ...], italic: bool) -> str:
    family = name.replace(" ", "+")
    if italic:
        pairs = [f"0,{w}" for w in weights] + [f"1,{w}" for w in weights]
        return f"family={family}:ital,wght@{';'.join(pairs)}"
    return f"family={family}:wght@{';'.join(str(w) for w in weights)}"


def main() -> int:
    ROOT.mkdir(parents=True, exist_ok=True)
    total = 0
    lines: list[str] = []

    for key, (name, weights, italic, subsets) in FAMILIES.items():
        url = f"{API}?{_spec(name, weights, italic)}&subset={subsets}&display=swap"
        try:
            css = _get(url)
        except OSError as exc:
            print(f"  {key}: unavailable ({exc})")
            continue

        seen: set[str] = set()
        index = 0
        for block in FACE_RE.findall(css):
            src = re.search(r"url\((https://[^)]+\.woff2)\)", block)
            weight = re.search(r"font-weight:\s*(\d+)", block)
            style = re.search(r"font-style:\s*(\w+)", block)
            if not src or not weight:
                continue
            slant = (style.group(1) if style else "normal") == "italic"
            filename = (
                f"{key}-{weight.group(1)}{'-italic' if slant else ''}-{index}.woff2"
            )
            index += 1
            if filename in seen:
                continue
            seen.add(filename)
            size = _download(src.group(1), ROOT / filename)
            total += size
            unicode_range = re.search(r"unicode-range:\s*([^;}]+)", block)
            span = (
                f";unicode-range:{unicode_range.group(1).strip()}"
                if unicode_range
                else ""
            )
            lines.append(
                "@font-face{{font-family:'{n}';font-style:{s};font-weight:{w};"
                "font-display:swap;src:url('fonts/{f}') format('woff2'){u}}}".format(
                    n=name,
                    s="italic" if slant else "normal",
                    w=weight.group(1),
                    f=filename,
                    u=span,
                )
            )
        print(f"  {key}: {len(seen)} faces")

    (ROOT.parent / "fonts.css").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} faces, {total / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
