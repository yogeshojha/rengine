from __future__ import annotations

from dataclasses import asdict

import pytest

from shared.definitions.domain_posture import (
    ANY,
    CHECKS,
    DKIM_MIN_BITS,
    GROUP_LABELS,
    NONE,
    QUERY_FIELD,
    SPF_ALL_LABELS,
    SPOOFABLE_KEYS,
    TONES,
    PostureCheck,
    PostureGroup,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("domain-posture.ts")


def test_the_frontend_mirror_carries_every_check_group_and_tone(mirror: Mirror):
    assert mirror.values("PostureCheck") == {c.value for c in PostureCheck}
    assert mirror.values("PostureGroup") == {g.value for g in PostureGroup}
    assert mirror.values("PostureTone") == set(TONES)
    assert mirror.labels("GROUP_LABELS") == GROUP_LABELS
    assert mirror.labels("SPF_ALL_LABELS") == SPF_ALL_LABELS


def test_the_frontend_mirror_carries_every_check_spec_in_order(mirror: Mirror):
    assert mirror.const("CHECKS") == [asdict(c) for c in CHECKS]


def test_the_frontend_mirror_carries_the_grammar_values(mirror: Mirror):
    assert mirror.const("POSTURE_FIELD") == QUERY_FIELD
    assert mirror.const("POSTURE_ANY") == ANY
    assert mirror.const("POSTURE_NONE") == NONE
    assert mirror.const("DKIM_MIN_BITS") == DKIM_MIN_BITS
    assert tuple(mirror.const("SPOOFABLE_KEYS")) == SPOOFABLE_KEYS
