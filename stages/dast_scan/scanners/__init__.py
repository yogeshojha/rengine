"""Fuzzers, discovered by module."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.plugins import by_name, classes_in_modules
from stages.vulnerability_scan.scanners.base import VulnScanner


class ScannerRegistrationError(RuntimeError):
    """A scanner module is invalid or duplicated."""


@lru_cache(maxsize=1)
def scanners() -> dict[str, type[VulnScanner]]:
    found = classes_in_modules(
        "stages.dast_scan.scanners", Path(__file__).parent, VulnScanner
    )
    return by_name(found, kind="scanner", error=ScannerRegistrationError)


__all__ = ["ScannerRegistrationError", "scanners"]
