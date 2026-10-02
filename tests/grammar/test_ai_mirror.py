from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.ai import MAX_CALLS_PAGE, MAX_CONNECTION_NAME, CostSource

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/ai.ts")


def _const(name: str) -> int:
    found = re.search(rf"export const {name} = (\d+);", MIRROR.read_text())
    assert found, f"{name} is missing from the mirror"
    return int(found.group(1))


def test_ai_limits_mirror():
    assert _const("MAX_CONNECTION_NAME") == MAX_CONNECTION_NAME
    assert _const("CALLS_PAGE") == MAX_CALLS_PAGE


def test_cost_sources_mirror():
    block = re.search(r"export const CostSource = \{(.*?)\}", MIRROR.read_text(), re.S)
    assert block, "CostSource is missing from the mirror"
    values = set(re.findall(r"'([a-z_]+)'", block.group(1)))
    assert values == {source.value for source in CostSource}
