from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.subdomain import SubdomainService
from shared.definitions.asset_query import HOST_QUERY
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.grammar


async def _rich_scan(estate, now):
    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["www.example.com", "old.example.com"], at=old)

    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run",
        ["www.example.com", "old.example.com"],
        at=now,
        ips=["10.0.0.1"],
        status=200,
        title="Welcome",
        tech=["nginx", "PHP"],
        webserver="nginx",
        cdn_name="cloudflare",
        favicon="1234567890",
        cname="edge.cdn.example.net",
    )
    await estate.hosts(
        "run",
        ["admin.example.com"],
        at=now,
        ips=["10.0.0.2"],
        status=200,
        title="Login",
        tech=["nginx"],
        webserver="nginx",
    )
    await estate.hosts(
        "run", ["dev.example.com"], at=now, ips=["10.0.0.2"], status=403, title="Denied"
    )
    await estate.hosts("run", ["dead.example.com"], at=now)
    await estate.ports(
        "run",
        [
            ("10.0.0.1", 443, "https"),
            ("10.0.0.2", 22, "ssh"),
            ("10.0.0.2", 3306, "mysql"),
        ],
        at=now,
    )
    await estate.assets(
        "run",
        ["www.example.com", "old.example.com"],
        at=now,
        ip="10.0.0.1",
        content_hash="deadbeef",
        jarm="29d3fd00029d29d00042d43d00041d",
        issuer="CN=Test CA",
    )
    await estate.assets(
        "run",
        ["admin.example.com"],
        at=now,
        ip="10.0.0.2",
        content_hash="cafebabe",
        jarm="29d3fd00029d29d00042d43d00041d",
        issuer="CN=Test CA",
    )
    return estate.scans["run"]


async def test_every_lead_count_equals_its_search(estate, now):
    scan = await _rich_scan(estate, now)
    service = SubdomainService(estate.session)

    leads = await service.leads(estate.project_id, scan, SubdomainFilter())
    assert leads.computed, "the lead set must be computed, not timed out"
    counted = [lead for lead in leads.leads if lead.count]
    assert counted, "the fixture should match at least one lead"

    for lead in counted:
        found = await service.search(
            estate.project_id, scan, SubdomainFilter(q=lead.query, limit=1)
        )
        assert found.error is None, f"{lead.query}: {found.error}"
        assert found.total == lead.count, (
            f"{lead.query}: lead says {lead.count}, search says {found.total}"
        )


async def test_every_group_count_equals_its_drill_down(estate, now):
    scan = await _rich_scan(estate, now)
    service = SubdomainService(estate.session)

    checked = 0
    for dimension in HOST_QUERY.dimensions:
        groups = await service.groups(
            estate.project_id, scan, SubdomainFilter(), dimension.key
        )
        for group in groups.groups:
            found = await service.search(
                estate.project_id, scan, SubdomainFilter(q=group.query, limit=1)
            )
            assert found.error is None, f"{group.query}: {found.error}"
            assert found.total == group.count, (
                f"{dimension.key}/{group.label}: group says {group.count}, "
                f"search says {found.total}"
            )
            checked += 1
    assert checked >= len(HOST_QUERY.dimensions), (
        "the fixture should populate every dimension"
    )


async def test_a_flag_and_its_negation_partition_the_scan(estate, now):
    scan = await _rich_scan(estate, now)
    service = SubdomainService(estate.session)

    async def total(q: str) -> int:
        r = await service.search(estate.project_id, scan, SubdomainFilter(q=q, limit=1))
        assert r.error is None, f"{q}: {r.error}"
        return r.total

    whole = await total("")
    for flag in (
        "is:live",
        "is:resolved",
        "is:cdn",
        "is:new",
        "is:sensitive",
        "is:auth",
    ):
        yes = await total(flag)
        no = await total(f"not {flag}")
        assert yes + no == whole, f"{flag}: {yes} + {no} != {whole}"
