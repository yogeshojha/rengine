from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.infostealer import (
    AUDIENCE_LABELS,
    QUERY_FIELD,
    SOURCE_NAME,
    SOURCE_URL,
    STANDING_LABELS,
    STRENGTH_LABELS,
    Audience,
    HostStanding,
    PasswordStrength,
)

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/infostealer.ts")


def _enum(name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", MIRROR.read_text(), re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"'([a-z_]+)'", block.group(1)))


def _const(name: str) -> str:
    found = re.search(rf"export const {name} = '([^']+)';", MIRROR.read_text())
    assert found, f"{name} is missing from the mirror"
    return found.group(1)


@pytest.mark.parametrize(
    ("name", "enum"),
    [
        ("Audience", Audience),
        ("PasswordStrength", PasswordStrength),
        ("HostStanding", HostStanding),
    ],
)
def test_enums_mirror(name, enum):
    assert _enum(name) == {member.value for member in enum}


def test_labels_mirror():
    text = MIRROR.read_text()
    for label in [
        *AUDIENCE_LABELS.values(),
        *STRENGTH_LABELS.values(),
        *STANDING_LABELS.values(),
    ]:
        assert f"label: '{label}'" in text, label


def test_constants_mirror():
    assert _const("SOURCE_NAME") == SOURCE_NAME
    assert _const("SOURCE_URL") == SOURCE_URL
    assert _const("QUERY_FIELD") == QUERY_FIELD
