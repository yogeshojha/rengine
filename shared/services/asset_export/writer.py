"""Turning rows into a file a person opens, without handing a spreadsheet a formula."""

from __future__ import annotations

import csv
import json
from typing import TYPE_CHECKING, Any

from shared.utils.text import strip_control

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

# a cell opening with one of these is read as a formula by excel and sheets
_FORMULA_LEAD = ("=", "+", "-", "@", "\t", "\r")
UTF8_BOM = "﻿"
_LIST_JOIN = "; "


def cell(value: Any) -> str:
    """One value as text: flattened, stripped of control characters, inert in a spreadsheet."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (list, tuple, set)):
        return _LIST_JOIN.join(cell(item) for item in value)
    if isinstance(value, dict):
        text = json.dumps(value, separators=(",", ":"), default=str)
    else:
        text = str(value)
    text = strip_control(text)
    if text.startswith(_FORMULA_LEAD):
        return "'" + text
    return text


def write_csv(path: Path, headers: list[str], rows: Iterable[dict]) -> int:
    """Excel reads a bare utf-8 file as latin-1, so the BOM is not optional."""
    written = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(UTF8_BOM)
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([cell(row.get(key)) for key in headers])
            written += 1
    return written


def write_json(path: Path, headers: list[str], rows: Iterable[dict]) -> int:
    """Streamed as an array, so a large export never assembles in memory."""
    written = 0
    with path.open("w", encoding="utf-8") as handle:
        handle.write("[")
        for row in rows:
            if written:
                handle.write(",")
            handle.write(
                "\n  "
                + json.dumps(
                    {key: row.get(key) for key in headers},
                    default=str,
                    ensure_ascii=False,
                )
            )
            written += 1
        handle.write("\n]\n" if written else "]\n")
    return written


def write_txt(path: Path, values: Iterator[str]) -> int:
    """One value per line, for the next tool in the chain."""
    written = 0
    with path.open("w", encoding="utf-8") as handle:
        for value in values:
            text = strip_control(str(value)).strip()
            if not text:
                continue
            handle.write(text + "\n")
            written += 1
    return written
