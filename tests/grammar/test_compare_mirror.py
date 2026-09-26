from __future__ import annotations

import pytest

from shared.definitions.compare import REFUSAL_REASON, RUN_FACETS, ChangeSignal, Refusal
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("compare.ts")


def test_the_frontend_mirror_carries_every_refusal_reason(mirror: Mirror):
    refusals = mirror.labels("REFUSAL")
    assert {name.lower() for name in refusals} == {r.value for r in Refusal}
    assert {name.lower(): text for name, text in refusals.items()} == REFUSAL_REASON


def test_every_change_signal_has_a_spec(mirror: Mirror):
    assert set(mirror.const("SIGNAL")) == {s.value for s in ChangeSignal}


def test_every_run_facet_has_a_place_in_the_banner(mirror: Mirror):
    order = mirror.const("RUN_FACET_ORDER")
    assert len(order) == len(set(order))
    assert {f.key for f in RUN_FACETS} <= set(order)
