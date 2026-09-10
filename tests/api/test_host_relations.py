"""A relation says how many hosts share a value, and drops what the whole estate shares."""

from __future__ import annotations

import pytest

from app.services.subdomain import _RELATION_CAP, SubdomainService
from shared.definitions.correlation import MIN_ESTATE_FOR_COMMON

pytestmark = pytest.mark.api


async def _related(estate, scan: str, name: str) -> dict:
    rows = await SubdomainService(estate.session).related(
        estate.project_id, estate.scans[scan], name
    )
    return {row.kind: row for row in rows}


async def test_a_shared_address_is_a_relation(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run", ["a.example.com", "b.example.com"], at=now, ips=["10.0.0.1"]
    )
    await estate.hosts("run", ["c.example.com"], at=now, ips=["10.0.0.9"])

    rows = await _related(estate, "run", "a.example.com")

    assert rows["ip"].hosts == ["b.example.com"]
    assert rows["ip"].total == 1


async def test_the_count_is_the_truth_not_the_length_of_the_list(estate, now):
    """The host list is capped; the number beside it must not be."""
    await estate.scan("example.com", "run", at=now)
    names = [f"h{i}.example.com" for i in range(_RELATION_CAP + 40)]
    await estate.hosts("run", names, at=now, cname="edge.example.net")
    # a bigger estate, so the shared cname is well under half of it
    await estate.hosts(
        "run", [f"other{i}.example.com" for i in range(_RELATION_CAP * 3)], at=now
    )

    rows = await _related(estate, "run", names[0])

    assert len(rows["cname"].hosts) == _RELATION_CAP
    assert rows["cname"].total == len(names) - 1


async def test_a_value_the_whole_estate_shares_is_not_a_relation(estate, now):
    """ "Same network" over every host is the estate, not a correlation."""
    await estate.scan("example.com", "run", at=now)
    names = [f"h{i}.example.com" for i in range(MIN_ESTATE_FOR_COMMON + 10)]
    await estate.hosts("run", names, at=now, cname="everything.example.net")

    rows = await _related(estate, "run", names[0])

    assert "cname" not in rows


async def test_a_small_scan_suppresses_nothing(estate, now):
    """Rarity has no meaning without a norm."""
    await estate.scan("example.com", "run", at=now)
    names = [f"h{i}.example.com" for i in range(4)]
    await estate.hosts("run", names, at=now, cname="edge.example.net")

    rows = await _related(estate, "run", names[0])

    assert rows["cname"].total == 3
