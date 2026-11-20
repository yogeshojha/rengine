from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.services.export import _check_filters
from shared.definitions.asset_query import MAX_QUERY_LENGTH
from shared.definitions.surface import EXPORTABLE_DIMENSIONS, SurfaceDimension

pytestmark = pytest.mark.api

WEB = SurfaceDimension.WEB_ASSETS.value
PROJECT = uuid.uuid4()


@pytest.mark.parametrize("dimension", EXPORTABLE_DIMENSIONS)
def test_every_exportable_dimension_takes_an_empty_filter(dimension):
    _check_filters(dimension, {}, PROJECT)


@pytest.mark.parametrize(
    "filters",
    [
        {"q": 5},
        {"q": ["a"]},
        {"q": "a" * (MAX_QUERY_LENGTH + 1)},
        {"pad": "x" * 1024},
        {"limit": 10**30},
        {"q": "and"},
        {"tech": ["a\x00b"]},
    ],
)
def test_a_filter_the_dimension_refuses_is_a_422(filters):
    with pytest.raises(HTTPException) as caught:
        _check_filters(WEB, filters, PROJECT)
    assert caught.value.status_code == 422


def test_a_table_filter_passes():
    _check_filters(WEB, {"q": "status:200", "tech": ["Nginx"], "sort": "name"}, PROJECT)
