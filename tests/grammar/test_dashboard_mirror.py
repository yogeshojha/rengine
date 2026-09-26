from __future__ import annotations

import pytest

from shared.definitions.dashboard import (
    SURFACE_RISK_ROWS,
    TIER_ACT_EPSS,
    TIER_LABELS,
    TIER_ORDER,
    ActivityKind,
    QueueTier,
)
from tests.grammar.ts_mirror import Mirror

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("dashboard.ts")


def test_the_frontend_mirror_carries_every_tier(mirror: Mirror):
    assert mirror.values("QueueTier") == {t.value for t in QueueTier}
    assert tuple(mirror.const("TIER_ORDER")) == TIER_ORDER
    assert mirror.labels("TIER_LABELS") == TIER_LABELS
    assert set(mirror.labels("TIER_HELP")) == set(TIER_ORDER)


def test_the_frontend_mirror_carries_the_act_threshold(mirror: Mirror):
    assert mirror.const("TIER_ACT_EPSS") == TIER_ACT_EPSS
    assert "epss:>=${TIER_ACT_EPSS}" in mirror.const("ACT_QUERY")


def test_the_frontend_mirror_carries_every_activity_kind(mirror: Mirror):
    assert mirror.values("ActivityKind") == {k.value for k in ActivityKind}


def test_the_frontend_mirror_carries_the_surface_risk_rows(mirror: Mirror):
    assert mirror.const("SURFACE_RISK_ROWS") == SURFACE_RISK_ROWS
