from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.scan_surface import (
    CLUSTER_SIGNAL_LABELS,
    DROP_REASON_LABELS,
    SURFACE_CLASS_LABELS,
    SURFACE_STATE_LABELS,
    TIER_LABELS,
    TIER_ORDER,
    ClusterSignal,
    DropReason,
    SurfaceClass,
    SurfaceState,
    Tier,
)

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/scan-surface.ts")


def _enum_values(text: str, name: str) -> set[str]:
    block = re.search(rf"export enum {name} \{{(.*?)\}}", text, re.S)
    assert block, f"{name} is missing from the mirror"
    return set(re.findall(r"= '([^']+)'", block.group(1)))


def test_the_frontend_mirror_carries_every_value():
    text = MIRROR.read_text()
    assert _enum_values(text, "SurfaceClass") == {c.value for c in SurfaceClass}
    assert _enum_values(text, "DropReason") == {r.value for r in DropReason}
    assert _enum_values(text, "ClusterSignal") == {s.value for s in ClusterSignal}
    assert _enum_values(text, "Tier") == {t.value for t in Tier}
    assert _enum_values(text, "SurfaceState") == {s.value for s in SurfaceState}


def test_the_frontend_mirror_carries_the_same_labels():
    text = MIRROR.read_text()
    for labels in (
        SURFACE_CLASS_LABELS,
        DROP_REASON_LABELS,
        CLUSTER_SIGNAL_LABELS,
        TIER_LABELS,
        SURFACE_STATE_LABELS,
    ):
        for label in labels.values():
            assert f"'{label}'" in text, label


def test_every_tier_is_ordered_and_labelled():
    assert set(TIER_ORDER) == {t.value for t in Tier}
    assert set(TIER_LABELS) == {t.value for t in Tier}
