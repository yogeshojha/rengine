from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.main import app as main_app
from app.services.scan_compare import ScanCompareService
from shared.definitions.asset_query import MAX_FACET_VALUE_LENGTH
from shared.definitions.compare import MAX_DIMENSION_LENGTH
from shared.definitions.surface import MAX_PAGE
from shared.models.endpoint import EndpointFilter
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
from shared.models.secret import SecretFilter
from shared.models.software import SoftwareFilter
from shared.models.subdomain import SubdomainFilter
from shared.models.timeline import FindingTimelineFilter, TimelineFilter
from shared.models.vulnerability import VulnerabilityFilter

pytestmark = pytest.mark.api

LONG = "x" * (MAX_FACET_VALUE_LENGTH + 1)


@pytest.mark.parametrize(
    ("model", "field"),
    [
        (SubdomainFilter, "tech"),
        (SubdomainFilter, "sources"),
        (TimelineFilter, "services"),
        (IpGroupFilter, "ids"),
        (IpGroupFilter, "countries"),
        (ServiceFilter, "services"),
        (VulnerabilityFilter, "templates"),
        (VulnerabilityFilter, "hosts"),
        (FindingTimelineFilter, "tags"),
    ],
)
def test_facet_value_length_is_bounded(model, field):
    model(**{field: ["x" * MAX_FACET_VALUE_LENGTH]})
    with pytest.raises(ValidationError):
        model(**{field: [LONG]})


@pytest.mark.parametrize("model", [IpGroupFilter, ServiceFilter])
@pytest.mark.parametrize(
    ("field", "value"),
    [("ports", -1), ("ports", 65536), ("asns", -1), ("asns", 2**32), ("asns", 10**30)],
)
def test_facet_numbers_are_bounded(model, field, value):
    with pytest.raises(ValidationError):
        model(**{field: [value]})


def test_facet_numbers_in_range_pass():
    assert ServiceFilter(ports=[0, 65535], asns=[4_294_967_295]).ports == [0, 65535]


@pytest.mark.parametrize(
    ("model", "field"),
    [
        (EndpointFilter, "endpoint_class"),
        (EndpointFilter, "source"),
        (EndpointFilter, "interest"),
        (EndpointFilter, "status_class"),
        (EndpointFilter, "sort"),
        (EndpointFilter, "direction"),
        (SoftwareFilter, "sort"),
        (SoftwareFilter, "direction"),
        (SecretFilter, "sort"),
        (SecretFilter, "direction"),
    ],
)
def test_filter_strings_are_bounded(model, field):
    with pytest.raises(ValidationError):
        model(**{field: "x" * 1000})


def _query_param(path: str, name: str) -> dict:
    operation = main_app.openapi()["paths"][path]["get"]
    return next(p for p in operation["parameters"] if p["name"] == name)["schema"]


@pytest.mark.parametrize("path", ["/api/v1/cves", "/api/v1/scans/compare/rows"])
def test_page_is_bounded(path):
    assert _query_param(path, "page")["maximum"] == MAX_PAGE


@pytest.mark.parametrize(
    "path", ["/api/v1/scans/compare/rows", "/api/v1/scans/compare/diff"]
)
def test_compare_dimension_is_bounded(path):
    schema = _query_param(path, "dimension")
    assert MAX_DIMENSION_LENGTH in (
        schema.get("maxLength"),
        *(s.get("maxLength") for s in schema.get("anyOf", ())),
    )


async def test_diff_refuses_an_unknown_dimension_before_comparing():
    with pytest.raises(HTTPException) as caught:
        await ScanCompareService(None).diff(
            baseline_id=None,
            current_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            dimension="bogus",
            verbs=[],
        )
    assert caught.value.status_code == 404


def test_secret_offset_is_bounded():
    SecretFilter(offset=100_000_000)
    with pytest.raises(ValidationError):
        SecretFilter(offset=10**30)
