from __future__ import annotations

from dataclasses import asdict

import pytest

from shared.definitions.hygiene import (
    ANY,
    CHECKS,
    GROUP_LABELS,
    NONE,
    TONES,
    HygieneCheck,
    HygieneGroup,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("hygiene.ts")


def test_the_frontend_mirror_carries_every_check_group_and_tone(mirror: Mirror):
    assert mirror.values("HygieneCheck") == {c.value for c in HygieneCheck}
    assert mirror.values("HygieneGroup") == {g.value for g in HygieneGroup}
    assert mirror.values("HygieneTone") == set(TONES)
    assert mirror.labels("GROUP_LABELS") == GROUP_LABELS


def test_the_frontend_mirror_carries_every_check_spec_in_order(mirror: Mirror):
    assert mirror.const("CHECKS") == [asdict(c) for c in CHECKS]


def test_the_frontend_mirror_carries_the_grammar_values(mirror: Mirror):
    field = CHECKS[0].query.split(":", 1)[0]
    assert mirror.const("HYGIENE_FIELD") == field
    assert mirror.const("HYGIENE_ANY") == ANY
    assert mirror.const("HYGIENE_NONE") == NONE
