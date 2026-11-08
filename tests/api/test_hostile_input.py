from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.definitions.asset_query import MAX_FACET_VALUE_LENGTH
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
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
