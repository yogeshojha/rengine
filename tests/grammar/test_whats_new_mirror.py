from __future__ import annotations

import pytest

from shared.definitions.whats_new import (
    BOUNTY_KINDS,
    GONE_KINDS,
    KIND_DIMENSION,
    KIND_LABELS,
    KIND_ORDER,
    NEW_WINDOWS,
    ROWS_PER_SECTION,
    SCAN_KINDS,
    VISUAL_FIELD_LABELS,
    Fact,
    NewBasis,
    NewKind,
    NewTab,
    ProgramRing,
    SubjectKind,
)
from tests.grammar.ts_mirror import Mirror, Ref

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("whats-new.ts")


def test_the_frontend_mirror_carries_every_value(mirror: Mirror):
    assert mirror.values("NewKind") == {k.value for k in NewKind}
    assert mirror.values("NewBasis") == {b.value for b in NewBasis}
    assert mirror.values("SubjectKind") == {s.value for s in SubjectKind}
    assert mirror.values("ProgramRing") == {r.value for r in ProgramRing}
    assert mirror.values("NewTab") == {t.value for t in NewTab}
    assert mirror.values("Fact") == {f.value for f in Fact}


def test_the_frontend_mirror_carries_every_kind_in_order(mirror: Mirror):
    assert tuple(mirror.const("KIND_ORDER")) == KIND_ORDER
    assert mirror.labels("KIND_LABELS") == KIND_LABELS
    assert set(mirror.const("KIND_NOUN")) == set(KIND_ORDER)
    assert set(mirror.const("KIND_ICONS")) == set(KIND_ORDER)


def test_the_frontend_mirror_groups_kinds_as_the_backend_does(mirror: Mirror):
    assert mirror.const("SCAN_KINDS") == set(SCAN_KINDS)
    assert mirror.const("BOUNTY_KINDS") == BOUNTY_KINDS
    assert mirror.const("GONE_KINDS") == GONE_KINDS


def test_the_frontend_mirror_maps_kinds_to_the_same_dimension(mirror: Mirror):
    surface = Mirror("surface.ts").enum("SurfaceDimension")
    dimension = {
        kind: surface[ref.name.removeprefix("SurfaceDimension.")]
        for kind, ref in mirror.const("KIND_DIMENSION").items()
        if isinstance(ref, Ref)
    }
    assert dimension == KIND_DIMENSION


def test_the_frontend_mirror_offers_every_window(mirror: Mirror):
    keys = [w["key"] for w in mirror.const("NEW_WINDOWS")]
    assert set(keys) == {mirror.const("SINCE_KEY"), *NEW_WINDOWS}


def test_the_frontend_mirror_carries_the_visual_fields_and_row_count(mirror: Mirror):
    assert mirror.labels("VISUAL_FIELD_LABELS") == VISUAL_FIELD_LABELS
    assert mirror.const("ROWS_SHOWN") == ROWS_PER_SECTION
