"""A correlation kind is only useful if every link in its chain exists."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.services.correlation_graph import _ASSET_KINDS, _HOST_KINDS
from shared.definitions.asset_query import HOST_QUERY
from shared.definitions.correlation import (
    CORRELATION_KIND_HELP,
    CORRELATION_KIND_LABELS,
    CORRELATION_KIND_ORDER,
    CorrelationKind,
)
from shared.models.http_asset import HttpAsset
from shared.models.subdomain import Subdomain
from shared.services.asset_query.groups import _DIMENSIONS

pytestmark = pytest.mark.grammar

MIRROR = Path("/app/frontend-config/correlation.ts")


@pytest.mark.parametrize("kind", list(CORRELATION_KIND_ORDER))
def test_every_kind_is_drawable_and_searchable(kind: str):
    assert kind in CORRELATION_KIND_LABELS, "the graph has no label for it"
    assert kind in CORRELATION_KIND_HELP, "the chip has nothing to say about it"
    assert kind in {*_HOST_KINDS, *_ASSET_KINDS}, "the graph cannot build a hub"
    assert kind in _DIMENSIONS, "a hub could not carry a drill-down token"
    assert HOST_QUERY.by_name.get(kind) is not None, "the token would not compile"


@pytest.mark.parametrize("kind", list(CORRELATION_KIND_ORDER))
def test_every_kind_reads_a_column_that_exists(kind: str):
    source = _HOST_KINDS.get(kind) or _ASSET_KINDS[kind]
    attr = source[0]
    model = Subdomain if kind in _HOST_KINDS else HttpAsset
    assert hasattr(model, attr), f"{model.__name__} has no {attr}"


def test_the_two_new_identities_are_wired():
    """tls_fingerprint and header_hash were stored and correlated by nothing."""
    assert CorrelationKind.CERT.value in _ASSET_KINDS
    assert CorrelationKind.HEADERS.value in _ASSET_KINDS
    assert _ASSET_KINDS[CorrelationKind.CERT.value][0] == "tls_fingerprint"
    assert _ASSET_KINDS[CorrelationKind.HEADERS.value][0] == "header_hash"


def test_the_frontend_mirror_carries_the_same_kinds():
    """config/correlation.ts mirrors the enum; a kind missing there draws no colour."""
    text = MIRROR.read_text()
    declared = set(re.findall(r"^\t[A-Z_]+ = '([^']+)',?$", text, re.M))
    assert declared == set(CORRELATION_KIND_ORDER)
    for kind in CORRELATION_KIND_ORDER:
        assert f"'{kind}'" in text
