from __future__ import annotations

import pytest

from shared.definitions.estate import (
    ESTATE_REASON_LABELS,
    ESTATE_REASON_ORDER,
    ESTATE_STRENGTH_LABELS,
    NEIGHBOUR_MAX_NAMES,
    PROVIDER_KIND_LABELS,
    EstateReason,
    EstateStrength,
    ProviderKind,
)
from shared.definitions.relations import RELATION_LABELS, RELATION_ORDER, TargetRelation
from tests.grammar.ts_mirror import Mirror, Ref, spreads

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("estate.ts")


@pytest.fixture(scope="module")
def relations() -> Mirror:
    return Mirror("relations.ts")


def test_the_frontend_mirror_carries_every_value(mirror: Mirror):
    assert mirror.values("EstateReason") == {r.value for r in EstateReason}
    assert mirror.values("EstateStrength") == {s.value for s in EstateStrength}
    assert mirror.values("ProviderKind") == {k.value for k in ProviderKind}


def test_the_frontend_mirror_carries_every_label(mirror: Mirror):
    own = {k: v for k, v in ESTATE_REASON_LABELS.items() if k not in RELATION_LABELS}
    assert mirror.labels("ESTATE_REASON_LABELS") == own
    assert spreads(mirror.const("ESTATE_REASON_LABELS")) == [Ref("RELATION_LABELS")]
    assert mirror.labels("ESTATE_STRENGTH_LABELS") == ESTATE_STRENGTH_LABELS
    assert mirror.labels("PROVIDER_KIND_LABELS") == PROVIDER_KIND_LABELS
    assert mirror.const("NEIGHBOUR_MAX_NAMES") == NEIGHBOUR_MAX_NAMES


def test_the_frontend_mirror_orders_reasons_strongest_first(mirror: Mirror):
    own = [r for r in ESTATE_REASON_ORDER if r not in RELATION_LABELS]
    order = mirror.const("ESTATE_REASON_ORDER")
    assert [r for r in order if isinstance(r, str)] == own
    # the relations sit where the backend puts them: after the certificate reasons
    spread = order.index(Ref("...Object.keys"))
    assert order[:spread] == list(ESTATE_REASON_ORDER[:spread])


def test_the_relation_labels_the_estate_spreads_match_the_backend(relations: Mirror):
    assert relations.values("TargetRelation") == {r.value for r in TargetRelation}
    assert tuple(relations.const("RELATION_ORDER")) == RELATION_ORDER
    assert relations.labels("RELATION_LABELS") == RELATION_LABELS
