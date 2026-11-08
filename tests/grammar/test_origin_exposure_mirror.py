from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.origin_exposure import OriginConfidence, OriginKind

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/origin-exposure.ts")


def _enum_values(text: str, name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"= '([^']+)'", block.group(1)))


def test_the_frontend_mirror_carries_every_value():
    text = MIRROR.read_text()
    assert _enum_values(text, "OriginKind") == {k.value for k in OriginKind}
    assert _enum_values(text, "OriginConfidence") == {c.value for c in OriginConfidence}
