"""A cached count is still a promise, so only a settled scope may be cached."""

from __future__ import annotations

import pytest

from shared.enums.scan import ScanStatus
from shared.models.asset_query import QueryLead, QueryLeads
from shared.models.subdomain import SubdomainFilter
from shared.services.asset_query import lead_cache

pytestmark = pytest.mark.grammar


def _answer(total: int) -> QueryLeads:
    return QueryLeads(
        leads=[QueryLead(query="is:live", description="d", group="g", count=total)],
        total=total,
        computed=True,
    )


class _Counter:
    def __init__(self, total: int = 7):
        self.calls = 0
        self.total = total

    async def __call__(self) -> QueryLeads:
        self.calls += 1
        return _answer(self.total)


async def _leads(estate, scan: str, build, facets: str = "{}") -> QueryLeads:
    return await lead_cache.leads(
        estate.session,
        dimension=f"test-{estate.project_id.hex[:8]}",
        scans=(estate.scans[scan],),
        facets=facets,
        build=build,
    )


async def test_a_finished_scan_is_computed_once(estate, now):
    await estate.scan("example.com", "done", at=now)
    build = _Counter()

    first = await _leads(estate, "done", build)
    second = await _leads(estate, "done", build)

    assert first.total == second.total == 7
    assert build.calls == 1, "the second read must come from the cache"


async def test_a_running_scan_is_never_cached(estate, now):
    """Its counts change under the reader, and a count must equal the rows it opens."""
    await estate.scan("example.com", "live", at=now, status=ScanStatus.RUNNING.value)
    build = _Counter()

    await _leads(estate, "live", build)
    await _leads(estate, "live", build)

    assert build.calls == 2


@pytest.mark.parametrize(
    "status", [ScanStatus.FAILED.value, ScanStatus.CANCELLED.value]
)
async def test_a_terminal_scan_is_cached_whatever_its_outcome(estate, now, status):
    await estate.scan("example.com", "over", at=now, status=status)
    build = _Counter()

    await _leads(estate, "over", build)
    await _leads(estate, "over", build)

    assert build.calls == 1


async def test_a_different_filter_is_a_different_answer(estate, now):
    await estate.scan("example.com", "done", at=now)
    plain, narrowed = _Counter(7), _Counter(3)

    a = await _leads(estate, "done", plain, facets='{"live":false}')
    b = await _leads(estate, "done", narrowed, facets='{"live":true}')

    assert (a.total, b.total) == (7, 3)
    assert plain.calls == narrowed.calls == 1


async def test_an_answer_that_did_not_compute_is_not_cached(estate, now):
    """A timed-out lead set must not be served for the next week."""
    await estate.scan("example.com", "done", at=now)
    calls = 0

    async def _timed_out() -> QueryLeads:
        nonlocal calls
        calls += 1
        return QueryLeads()

    await _leads(estate, "done", _timed_out, facets='{"case":"timeout"}')
    await _leads(estate, "done", _timed_out, facets='{"case":"timeout"}')

    assert calls == 2


async def test_facets_of_ignores_what_cannot_change_a_count(estate):
    a = lead_cache.facets_of(SubdomainFilter(q="anything", page=1, size=50))
    b = lead_cache.facets_of(SubdomainFilter(q="other", page=9, size=200))
    c = lead_cache.facets_of(SubdomainFilter(live=True))

    assert a == b, "paging and the search box do not change a lead count"
    assert a != c, "a facet does"
