from __future__ import annotations

import pytest

from app.services.endpoint import _STATUS_CLASSES, EndpointService
from shared.models.endpoint import EndpointFilter

pytestmark = pytest.mark.grammar


async def _scan(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.endpoints(
        "run", ["/", "/login", "/admin"], at=now, status=200, kind="page"
    )
    await estate.endpoints(
        "run",
        ["/api/v1/users", "/api/v1/orders"],
        at=now,
        status=401,
        kind="api",
        sources=["crawl"],
        params=2,
    )
    await estate.endpoints(
        "run", ["/assets/app.css", "/assets/logo.png"], at=now, kind="style"
    )
    await estate.endpoints(
        "run", ["/old"], at=now, status=500, kind="page", interest=["admin"]
    )
    return estate.scans["run"]


async def test_facet_counts_add_up_to_the_total(estate, now):
    scan = await _scan(estate, now)
    facets = await EndpointService(estate.session).facets(scan, EndpointFilter())

    assert facets.total == 8
    assert sum(f.count for f in facets.endpoint_class) == facets.total
    assert sum(f.count for f in facets.status_class) == facets.total


async def test_status_keeps_its_declared_order_not_a_count_order(estate, now):
    scan = await _scan(estate, now)
    facets = await EndpointService(estate.session).facets(scan, EndpointFilter())

    order = [f.value for f in facets.status_class]
    assert order == sorted(order, key=_STATUS_CLASSES.index)
    assert order[0] == "2xx", (
        "the most common class here is 'none', which must not lead"
    )


async def test_a_narrowed_reach_agrees_with_an_unnarrowed_one(estate, now):
    scan = await _scan(estate, now)
    service = EndpointService(estate.session)

    plain = await service.facets(scan, EndpointFilter())
    narrowed = await service.facets(scan, EndpointFilter(q="not is:nonexistentflag"))
    if narrowed.total == 0:
        narrowed = await service.facets(scan, EndpointFilter(host="www.example.com"))

    assert narrowed.total == plain.total
    assert [(f.value, f.count) for f in narrowed.endpoint_class] == [
        (f.value, f.count) for f in plain.endpoint_class
    ]
    assert [(f.value, f.count) for f in narrowed.status_class] == [
        (f.value, f.count) for f in plain.status_class
    ]


async def test_a_filter_actually_narrows(estate, now):
    scan = await _scan(estate, now)
    service = EndpointService(estate.session)

    only_api = await service.facets(scan, EndpointFilter(endpoint_class="api"))
    assert only_api.total == 2
    assert [f.value for f in only_api.endpoint_class] == ["api"]


async def test_static_total_counts_within_the_reach(estate, now):
    scan = await _scan(estate, now)
    service = EndpointService(estate.session)

    plain = await service.facets(scan, EndpointFilter())
    assert plain.static_total == 2, "the two style rows"

    api = await service.facets(scan, EndpointFilter(endpoint_class="api"))
    assert api.static_total == 0


async def test_summary_totals_agree_with_the_facets(estate, now):
    scan = await _scan(estate, now)
    service = EndpointService(estate.session)

    facets = await service.facets(scan, EndpointFilter())
    summary = await service.summary(scan)

    assert summary.total == facets.total
    assert summary.by_class == {f.value: f.count for f in facets.endpoint_class}
    live = next((f.count for f in facets.status_class if f.value == "2xx"), 0)
    assert summary.live == live
    assert summary.with_params == 2
    assert summary.interesting == 1


async def test_hide_static_narrows_the_host_rollup(estate, now):
    scan = await _scan(estate, now)
    service = EndpointService(estate.session)

    everything = await service.hosts(scan, EndpointFilter())
    without_static = await service.hosts(scan, EndpointFilter(hide_static=True))

    assert everything.total_endpoints == 8
    assert without_static.total_endpoints == 6, "the two style rows must be gone"
    assert without_static.items[0].subtree_count == 6
