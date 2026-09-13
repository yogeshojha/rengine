from __future__ import annotations

import pytest

from app.services.subdomain import SubdomainService
from shared.definitions.correlation import (
    SCREENSHOT_DISTANCE,
    SCREENSHOT_MIN_POPCOUNT,
)
from shared.models.subdomain import SubdomainFilter
from shared.services.asset_query.renders import cluster, cluster_of, is_identity
from shared.utils.imagehash import distance, hex_digest, to_signed, to_unsigned

pytestmark = pytest.mark.grammar

_PAGE = 0x0030242430D41010
_NEAR = 0x0030242430D41012
_FAR = 0x7F3C1908A4D6E251


def test_a_blank_render_is_not_an_identity():
    assert not is_identity(0)
    assert not is_identity(to_signed(0xFFFFFFFFFFFFFFFF))
    assert not is_identity(None)
    assert is_identity(_PAGE)


def test_the_popcount_floor_is_the_whole_rule():
    below = to_signed((1 << (SCREENSHOT_MIN_POPCOUNT - 1)) - 1)
    at = to_signed((1 << SCREENSHOT_MIN_POPCOUNT) - 1)
    assert not is_identity(below)
    assert is_identity(at)


def test_a_near_identical_render_joins_the_cluster():
    assert distance(_PAGE, _NEAR) <= SCREENSHOT_DISTANCE
    groups = cluster({_PAGE: 9, _NEAR: 2, _FAR: 1})
    assert len(groups) == 2
    biggest = groups[0]
    assert biggest.value == _PAGE
    assert biggest.count == 11
    assert set(biggest.hashes) == {_PAGE, _NEAR}


def test_a_cluster_counts_every_hash_its_filter_would_reach():
    groups = cluster({_PAGE: 9, _NEAR: 2, _FAR: 1})
    for found in groups:
        reached = {_PAGE: 9, _NEAR: 2, _FAR: 1}
        assert found.count == sum(
            n
            for h, n in reached.items()
            if distance(found.value, h) <= SCREENSHOT_DISTANCE
        )


def test_a_blank_hash_never_becomes_a_representative():
    groups = cluster({0: 40, _PAGE: 2})
    assert [g.value for g in groups] == [_PAGE]


def test_a_digest_round_trips():
    assert hex_digest(_PAGE) == "0030242430d41010"
    assert to_signed(to_unsigned(-1)) == -1
    assert len(hex_digest(to_signed(0xFFFFFFFFFFFFFFFF))) == 16


def test_cluster_of_prefers_the_largest_reaching_cluster():
    groups = cluster({_PAGE: 9, _NEAR: 2, _FAR: 1})
    assert cluster_of(groups, _NEAR).value == _PAGE
    assert cluster_of(groups, None) is None


async def test_the_render_group_count_equals_its_search(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run", ["a.example.com", "b.example.com"], at=now, status=200, phash=_PAGE
    )
    await estate.hosts("run", ["c.example.com"], at=now, status=200, phash=_NEAR)
    await estate.hosts("run", ["d.example.com"], at=now, status=200, phash=_FAR)
    await estate.hosts("run", ["blank.example.com"], at=now, status=200, phash=1)
    scan = estate.scans["run"]
    service = SubdomainService(estate.session)

    groups = await service.groups(
        estate.project_id, scan, SubdomainFilter(), "screenshot"
    )
    assert groups.groups, "the screenshot dimension produced nothing"
    for group in groups.groups:
        found = await service.search(
            estate.project_id, scan, SubdomainFilter(q=group.query, limit=1)
        )
        assert found.error is None, f"{group.query}: {found.error}"
        assert found.total == group.count, (
            f"{group.query}: group says {group.count}, search says {found.total}"
        )
    assert groups.groups[0].count == 3, "the near-identical render did not join"


async def test_a_blank_render_is_reported_apart_from_the_groups(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run", ["a.example.com", "b.example.com"], at=now, status=200, phash=_PAGE
    )
    await estate.hosts("run", ["blank.example.com"], at=now, status=200, phash=1)
    await estate.hosts("run", ["none.example.com"], at=now, status=200)
    scan = estate.scans["run"]

    result = await SubdomainService(estate.session).renders(
        estate.project_id, scan, SubdomainFilter()
    )
    assert result.grouped == 2
    assert result.blank == 1
    assert result.unrendered == 1
    assert result.grouped + result.ungrouped + result.blank + result.unrendered == 4
