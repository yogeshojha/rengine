"""`is:new` needs a baseline: a target's first scan reports nothing new."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.subdomain import SubdomainService
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.grammar

FIRST = ["a.example.com", "b.example.com", "c.example.com"]
SECOND = [*FIRST, "d.example.com", "e.example.com"]


async def _hosts(estate, q: str, scan: str) -> int:

    result = await SubdomainService(estate.session).search(
        estate.project_id, estate.scans[scan], SubdomainFilter(q=q, limit=1)
    )
    assert result.error is None, result.error
    return result.total


async def test_first_scan_reports_nothing_new(estate, now):
    await estate.scan("example.com", "only", at=now)
    await estate.hosts("only", SECOND, at=now)

    assert await _hosts(estate, "is:new", "only") == 0
    assert await _hosts(estate, "", "only") == len(SECOND)


async def test_second_scan_reports_only_what_the_first_missed(estate, now):
    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", FIRST, at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", SECOND, at=now)

    assert await _hosts(estate, "is:new", "second") == 2
    assert await _hosts(estate, "not is:new", "second") == 3
    assert await _hosts(estate, "", "second") == 5


async def test_new_and_not_new_partition_the_scan(estate, now):
    """The null-safe NOT rule: the two halves must add up to the whole."""
    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", FIRST, at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", SECOND, at=now, status=200)

    total = await _hosts(estate, "", "second")
    new = await _hosts(estate, "is:new", "second")
    rest = await _hosts(estate, "not is:new", "second")
    assert new + rest == total


async def test_a_baseline_belongs_to_one_target(estate, now):
    """Another target's earlier scan must never count as this target's baseline."""
    old = now - timedelta(days=7)
    await estate.scan("other.com", "other", at=old)
    await estate.hosts("other", ["x.other.com"], at=old)
    await estate.scan("example.com", "only", at=now)
    await estate.hosts("only", SECOND, at=now)

    assert await _hosts(estate, "is:new", "only") == 0


async def test_a_later_scan_is_not_a_baseline(estate, now):
    """Only an EARLIER scan baselines a run; a newer one must be ignored."""
    await estate.scan("example.com", "middle", at=now)
    await estate.hosts("middle", SECOND, at=now)
    later = now + timedelta(days=7)
    await estate.scan("example.com", "later", at=later)
    await estate.hosts("later", SECOND, at=later)

    assert await _hosts(estate, "is:new", "middle") == 0
    assert await _hosts(estate, "is:new", "later") == 0


async def test_project_scope_judges_newness_per_target(estate, now):
    """One target with history and one without: only the first may report new hosts."""

    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", FIRST, at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", SECOND, at=now)
    await estate.scan("fresh.com", "fresh", at=now)
    await estate.hosts("fresh", ["a.fresh.com", "b.fresh.com"], at=now)

    scope = [estate.scans["second"], estate.scans["fresh"]]
    result = await SubdomainService(estate.session).search(
        estate.project_id, scope, SubdomainFilter(q="is:new", limit=10)
    )
    assert result.error is None, result.error
    assert result.total == 2
    assert {r.name for r in result.items} == {"d.example.com", "e.example.com"}


async def test_the_facet_filter_agrees_with_the_query(estate, now):
    """`_apply_filter` is a second code path onto the same predicate."""

    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", FIRST, at=old)
    await estate.scan("example.com", "second", at=now)
    await estate.hosts("second", SECOND, at=now)

    service = SubdomainService(estate.session)
    scope = estate.scans["second"]
    by_facet = await service.search(
        estate.project_id, scope, SubdomainFilter(new=True, limit=1)
    )
    by_query = await service.search(
        estate.project_id, scope, SubdomainFilter(q="is:new", limit=1)
    )
    assert by_facet.total == by_query.total == 2
