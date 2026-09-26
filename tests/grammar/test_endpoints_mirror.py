from __future__ import annotations

import pytest

from shared.definitions.asset_query import STATUS_CLASSES
from shared.definitions.endpoints import (
    ARCHIVE_SOURCES,
    CLASS_LABELS,
    ENDPOINT_CLASSES,
    INTEREST_HELP,
    INTEREST_LABELS,
    NOISE_RULE_HELP,
    NOISE_RULE_LABELS,
    PASSIVE_SOURCES,
    PROBE_COVERAGE_SOURCE,
    SENSITIVE_INTERESTS,
    SOURCE_LABELS,
    STATIC_CLASSES,
    WHY_INTERESTS,
    EndpointClass,
    EndpointSource,
    FolderGlyph,
    NoiseRule,
)
from tests.grammar.ts_mirror import Mirror, Ref, spreads

pytestmark = pytest.mark.grammar


@pytest.fixture(scope="module")
def mirror() -> Mirror:
    return Mirror("endpoints.ts")


def test_the_frontend_mirror_carries_every_endpoint_class(mirror: Mirror):
    assert mirror.values("EndpointClass") == {c.value for c in EndpointClass}
    assert set(mirror.const("ENDPOINT_CLASS_ORDER")) == set(ENDPOINT_CLASSES)
    assert mirror.labels("ENDPOINT_CLASS_LABELS") == CLASS_LABELS
    assert mirror.const("STATIC_CLASSES") == STATIC_CLASSES


def test_the_frontend_mirror_carries_every_folder_glyph(mirror: Mirror):
    glyphs = {g.value for g in FolderGlyph}
    assert mirror.values("FolderGlyph") == glyphs
    assert set(mirror.const("FOLDER_GLYPH_ICONS")) == glyphs
    assert set(mirror.labels("FOLDER_GLYPH_LABELS")) == glyphs


def test_the_frontend_mirror_carries_every_source(mirror: Mirror):
    assert mirror.values("EndpointSource") == {s.value for s in EndpointSource}
    assert mirror.labels("SOURCE_LABELS") == SOURCE_LABELS
    assert mirror.const("PROBE_COVERAGE_SOURCE") == PROBE_COVERAGE_SOURCE
    coverage = mirror.const("COVERAGE_SOURCE_LABELS")
    assert spreads(coverage) == [Ref("SOURCE_LABELS")]
    assert mirror.labels("COVERAGE_SOURCE_LABELS") == {
        PROBE_COVERAGE_SOURCE: "Verification"
    }
    assert mirror.const("PASSIVE_SOURCES") == PASSIVE_SOURCES
    assert mirror.const("ARCHIVE_SOURCES") == ARCHIVE_SOURCES


def test_the_frontend_mirror_carries_every_noise_rule(mirror: Mirror):
    assert mirror.values("NoiseRule") == {r.value for r in NoiseRule}
    assert mirror.const("NOISE_RULE_ORDER") == [r.value for r in NoiseRule]
    assert mirror.labels("NOISE_RULE_LABELS") == NOISE_RULE_LABELS
    assert mirror.labels("NOISE_RULE_HELP") == NOISE_RULE_HELP


def test_the_frontend_mirror_carries_every_param_and_path_interest(mirror: Mirror):
    assert mirror.labels("INTEREST_LABELS") == INTEREST_LABELS
    assert mirror.labels("INTEREST_HELP") == INTEREST_HELP
    assert tuple(mirror.const("WHY_INTERESTS")) == WHY_INTERESTS
    assert mirror.const("SENSITIVE_INTEREST") == SENSITIVE_INTERESTS
    assert set(mirror.labels("INTEREST_TONE")) <= set(INTEREST_LABELS)


def test_the_frontend_mirror_carries_every_status_class(mirror: Mirror):
    assert tuple(mirror.const("STATUS_CLASSES")) == STATUS_CLASSES
    assert set(mirror.labels("STATUS_CLASS_LABELS")) == set(STATUS_CLASSES)
    assert set(mirror.labels("STATUS_CLASS_FILL")) == set(STATUS_CLASSES)
