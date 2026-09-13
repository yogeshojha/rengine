from __future__ import annotations

import re
from pathlib import Path

import pytest

from shared.definitions.asset_query import HOST_QUERY
from shared.definitions.correlation import (
    CORRELATION_KIND_HELP,
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    CORRELATION_RELATION_PHRASE,
    CorrelationKind,
)
from shared.services.asset_query.groups import _DIMENSIONS, DERIVED_DIMENSIONS
from shared.services.correlation.kinds import KINDS

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/correlation.ts")


@pytest.mark.parametrize("kind", list(CORRELATION_KIND_ORDER))
def test_every_kind_is_drawable_and_searchable(kind: str):
    assert kind in CORRELATION_KIND_LABELS, "the graph has no label for it"
    assert kind in CORRELATION_KIND_HELP, "the chip has nothing to say about it"
    assert kind in CORRELATION_RELATION_PHRASE, "Related has nothing to call it"
    assert kind in KINDS, "the engine cannot build a hub"
    assert kind in {
        *_DIMENSIONS,
        *DERIVED_DIMENSIONS,
    }, "a hub could not carry a drill-down token"
    assert HOST_QUERY.by_name.get(kind) is not None, "the token would not compile"


@pytest.mark.parametrize("kind", list(CORRELATION_KIND_ORDER))
def test_every_kind_reads_a_column_that_exists(kind: str):
    spec = KINDS[kind]
    assert hasattr(spec.model, spec.attr), f"{spec.model.__name__} has no {spec.attr}"


def test_the_grouping_dimensions_come_from_the_one_registry():
    for kind, spec in KINDS.items():
        if spec.derived:
            continue
        _build, field, operator, asset = _DIMENSIONS[kind]
        assert field == kind
        assert operator == spec.operator
        assert asset == spec.asset


def test_the_identities_read_off_the_http_asset():
    assert KINDS[CorrelationKind.CERT.value].asset
    assert KINDS[CorrelationKind.CERT.value].attr == "tls_fingerprint"
    assert KINDS[CorrelationKind.HEADERS.value].asset
    assert KINDS[CorrelationKind.HEADERS.value].attr == "header_hash"


def test_the_frontend_mirror_carries_the_same_kinds():
    text = MIRROR.read_text()
    declared = set(re.findall(r"^\t[A-Z_]+ = '([^']+)',?$", text, re.M))
    assert declared == set(CORRELATION_KIND_ORDER)
    for kind in CORRELATION_KIND_ORDER:
        assert f"'{kind}'" in text
