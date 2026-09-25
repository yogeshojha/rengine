from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.services.ip_address import IpAddressService
from app.services.subdomain import SubdomainService
from shared.models.scan_correlation import IpGroupFilter
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.grammar


async def _total(estate, scan, q: str) -> int:
    result = await SubdomainService(estate.session).search(
        estate.project_id, scan, SubdomainFilter(q=q, limit=1)
    )
    assert result.error is None, f"{q}: {result.error}"
    return result.total


async def test_host_matches_whatever_case_the_query_is_typed_in(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["admin.example.com", "www.example.com"], at=now)
    scan = estate.scans["run"]

    assert await _total(estate, scan, "host:ADMIN") == 1
    assert await _total(estate, scan, "host:[Admin,WWW]") == 2
    assert await _total(estate, scan, "host=ADMIN.EXAMPLE.COM") == 1
    assert await _total(estate, scan, "host!=Admin.Example.Com") == 1
    assert await _total(estate, scan, "not host:ADMIN") == 1
    assert await _total(estate, scan, "admin") == 1, "free text reads the host too"


async def test_a_host_name_is_refused_unless_lowercase(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["api.example.com"], at=now)

    with pytest.raises(IntegrityError):
        await estate.session.execute(
            text("UPDATE subdomains SET name = 'API.example.com'")
        )


async def test_a_list_value_matches_inside_the_array_only(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["a.example.com"], at=now, tech=["Nginx", "PHP"])
    await estate.hosts("run", ["b.example.com"], at=now, tech=[])
    scan = estate.scans["run"]

    assert await _total(estate, scan, "tech:nginx") == 1
    assert await _total(estate, scan, "tech:[php,jenkins]") == 1
    assert await _total(estate, scan, "not tech:nginx") == 1
    assert await _total(estate, scan, "tech:jenkins") == 0


async def test_an_address_page_past_the_end_still_counts_every_match(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["a.example.com"], at=now, ips=["192.0.2.1"])
    await estate.hosts("run", ["b.example.com"], at=now, ips=["192.0.2.2"])
    service = IpAddressService(estate.session)
    scan = estate.scans["run"]

    first = await service.search(scan, IpGroupFilter(limit=1))
    beyond = await service.search(scan, IpGroupFilter(limit=1, offset=10))

    assert first.total == beyond.total == 2
    assert len(first.items) == 1
    assert beyond.items == []
