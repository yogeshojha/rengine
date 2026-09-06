#!/usr/bin/env python3
"""Vendor the report fonts. Run on a checkout; the files are committed so an offline box still renders.

One file per family, weight and style — never Google's per-script split. Several @font-face
rules that share a family and differ only by unicode-range make WeasyPrint shape against one
subset and rasterise from another, which printed Greek titles as scrambled Latin.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

DEFAULT_ROOT = Path(__file__).resolve().parent.parent / "reports" / "assets" / "fonts"
API = "https://fonts.googleapis.com/css2"
# a UA that takes woff but predates unicode-range, so the API answers with one whole file
UA = (
    "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36"
)

# a body face carries the scripts a real estate is named in; display and mono stay latin
WIDE = "latin,latin-ext,greek,cyrillic"
LATIN = "latin,latin-ext"
MONO = "latin"

# what to keep after the download, per subset choice
UNICODES = {
    WIDE: "U+0000-024F,U+0259,U+0300-036F,U+0370-03FF,U+0400-04FF,U+1E00-1EFF,"
    "U+2000-206F,U+2070-209F,U+20A0-20CF,U+2100-214F,U+2190-21FF,U+2200-22FF,U+25A0-25FF,U+2E00-2E7F",
    LATIN: "U+0000-024F,U+0259,U+0300-036F,U+1E00-1EFF,U+2000-206F,U+2070-209F,"
    "U+20A0-20CF,U+2100-214F,U+2190-21FF,U+2200-22FF,U+25A0-25FF,U+2E00-2E7F",
    MONO: "U+0000-024F,U+0259,U+0300-036F,U+2000-206F,U+2070-209F,U+20A0-20CF,"
    "U+2100-214F,U+2190-21FF,U+2200-22FF,U+25A0-25FF",
}

FAMILIES: dict[str, tuple[str, tuple[int, ...], bool, str]] = {
    "inter": ("Inter", (400, 500, 600, 700), False, WIDE),
    "space-grotesk": ("Space Grotesk", (400, 500, 700), False, LATIN),
    "ibm-plex-sans": ("IBM Plex Sans", (400, 600, 700), True, WIDE),
    "source-serif": ("Source Serif 4", (400, 600, 700), True, WIDE),
    "jetbrains-mono": ("JetBrains Mono", (400, 700), False, MONO),
    "ibm-plex-mono": ("IBM Plex Mono", (400, 600), False, MONO),
}

FACE_RE = re.compile(r"@font-face\s*\{(.*?)\}", re.S)


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})  # noqa: S310
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        return response.read()


def _spec(name: str, weights: tuple[int, ...], italic: bool) -> str:
    family = name.replace(" ", "+")
    if italic:
        pairs = [f"0,{w}" for w in weights] + [f"1,{w}" for w in weights]
        return f"family={family}:ital,wght@{';'.join(pairs)}"
    return f"family={family}:wght@{';'.join(str(w) for w in weights)}"


def _trim(raw: bytes, unicodes: str) -> bytes:
    """Keep the ranges a report can print, and write one woff2."""
    font = TTFont(io.BytesIO(raw))
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.drop_tables = ["FFTM"]
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=subset.parse_unicodes(unicodes))
    subsetter.subset(font)
    font.flavor = "woff2"
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    root = parser.parse_args().root
    root.mkdir(parents=True, exist_ok=True)
    for stale in root.glob("*.woff2"):
        stale.unlink()
    total = 0
    lines: list[str] = []

    for key, (name, weights, italic, subsets) in FAMILIES.items():
        url = f"{API}?{_spec(name, weights, italic)}&subset={subsets}&display=swap"
        try:
            css = _fetch(url).decode("utf-8")
        except OSError as exc:
            print(f"  {key}: unavailable ({exc})")
            continue

        faces = 0
        for block in FACE_RE.findall(css):
            src = re.search(r"url\((https://[^)]+)\)", block)
            weight = re.search(r"font-weight:\s*(\d+)", block)
            style = re.search(r"font-style:\s*(\w+)", block)
            if not src or not weight:
                continue
            if "unicode-range" in block:
                print(f"  {key}: the API split this family; refusing a split face")
                return 1
            slant = (style.group(1) if style else "normal") == "italic"
            filename = f"{key}-{weight.group(1)}{'-italic' if slant else ''}.woff2"
            data = _trim(_fetch(src.group(1)), UNICODES[subsets])
            (root / filename).write_bytes(data)
            total += len(data)
            faces += 1
            lines.append(
                f"@font-face{{font-family:'{name}';"
                f"font-style:{'italic' if slant else 'normal'};"
                f"font-weight:{weight.group(1)};font-display:swap;"
                f"src:url('fonts/{filename}') format('woff2')}}"
            )
        print(f"  {key}: {faces} faces")

    (root.parent / "fonts.css").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(lines)} faces, {total / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
