from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.scan_admission import AUTOMATIC, MAX_CONCURRENT_SCANS

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/scan-admission.ts")


def _const(name: str) -> int:
    found = re.search(rf"export const {name} = (\d+);", MIRROR.read_text())
    assert found, f"{name} is missing from the mirror"
    return int(found.group(1))


def test_the_limit_bounds_match_the_mirror():
    assert _const("AUTOMATIC") == AUTOMATIC
    assert _const("MAX_CONCURRENT_SCANS") == MAX_CONCURRENT_SCANS
