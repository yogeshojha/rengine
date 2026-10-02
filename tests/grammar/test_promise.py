from __future__ import annotations

from datetime import timedelta

import pytest

from app.services.endpoint import EndpointService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from app.services.secret import SecretService
from app.services.software import SoftwareService
from app.services.subdomain import SubdomainService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.asset_query import ALL_TAB, HOST_QUERY
from shared.definitions.vulnerabilities import ACTIVE_TAB, SUPPRESSED_STATES
from shared.models.endpoint import EndpointFilter
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
from shared.models.secret import SecretFilter
from shared.models.software import SoftwareFilter
from shared.models.subdomain import SubdomainFilter
from shared.models.vulnerability import VulnerabilityFilter

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
        phash=0x0030242430D41010,
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
        phash=0x0030242430D41012,
    )
    await estate.hosts(
        "run",
        ["dev.example.com"],
        at=now,
        ips=["10.0.0.2"],
        status=403,
        title="Denied",
        phash=0x7F3C1908A4D6E251,
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


async def _tab_rows(tabs, opened):
    assert tabs.computed, "the tab counts must be computed"
    for key, count in tabs.counts.items():
        found = await opened(key)
        assert found.error is None, f"{key}: {found.error}"
        assert found.total == count, f"{key}: tab says {count}, rows {found.total}"


@pytest.mark.parametrize(
    "f",
    [
        SubdomainFilter(),
        SubdomainFilter(q="tech:nginx"),
        SubdomainFilter(tech=["nginx"], statuses=["4xx"]),
        SubdomainFilter(q="ip:10.0.0.2 or title:Welcome"),
    ],
)
async def test_every_status_tab_equals_the_rows_it_opens(estate, now, f):
    scan = await _rich_scan(estate, now)
    service = SubdomainService(estate.session)

    async def opened(key):
        statuses = [] if key == ALL_TAB else [key]
        return await service.search(
            estate.project_id,
            scan,
            f.model_copy(update={"statuses": statuses, "limit": 1}),
        )

    await _tab_rows(await service.tabs(estate.project_id, scan, f), opened)


async def test_every_class_tab_equals_the_rows_it_opens(estate, now):
    scan = await _rich_scan(estate, now)
    await estate.endpoints("run", ["/", "/about", "/login"], at=now, status=200)
    await estate.endpoints("run", ["/api/v1/users"], at=now, status=200, kind="api")
    await estate.endpoints("run", ["/app.js"], at=now, status=404, kind="script")
    services = PortService(estate.session)
    endpoints = EndpointService(estate.session)

    for f in (ServiceFilter(), ServiceFilter(q="ip:10.0.0.2", classes=["web"])):

        async def service_rows(key, f=f):
            classes = [] if key == ALL_TAB else [key]
            return await services.search(
                scan, f.model_copy(update={"classes": classes, "limit": 1})
            )

        await _tab_rows(await services.tabs(scan, f), service_rows)

    for f in (EndpointFilter(), EndpointFilter(q="status:200", endpoint_class="api")):

        async def endpoint_rows(key, f=f):
            klass = None if key == ALL_TAB else key
            return await endpoints.search(
                scan, f.model_copy(update={"endpoint_class": klass, "size": 1})
            )

        await _tab_rows(await endpoints.tabs(scan, f), endpoint_rows)


async def test_every_exposure_tab_equals_the_rows_it_opens(estate, now):
    scan = await _rich_scan(estate, now)
    service = IpAddressService(estate.session)
    for f in (IpGroupFilter(), IpGroupFilter(q="port:22")):

        async def opened(key, f=f):
            exposure = [] if key == ALL_TAB else [key]
            return await service.search(
                scan, f.model_copy(update={"exposure": exposure, "limit": 1})
            )

        await _tab_rows(await service.tabs(scan, f), opened)


async def test_every_review_tab_equals_the_rows_it_opens(estate, now):
    scan = await _rich_scan(estate, now)
    await estate.vulns("run", [("exposed-git", "high"), ("weak-tls", "low")], at=now)
    service = VulnerabilityService(estate.session)
    f = VulnerabilityFilter(q="severity:high", include_info=True)

    async def opened(key):
        if key == ALL_TAB:
            update = {"states": [], "include_suppressed": True}
        elif key == ACTIVE_TAB:
            update = {"states": [], "include_suppressed": False}
        else:
            update = {"states": [key], "include_suppressed": key in SUPPRESSED_STATES}
        return await service.search(scan, f.model_copy(update={**update, "limit": 1}))

    await _tab_rows(await service.tabs(scan, f), opened)


async def test_a_grammar_tab_count_equals_the_rows_it_opens(estate, now):
    scan = await _rich_scan(estate, now)
    software = SoftwareService(estate.session)
    secrets = SecretService(estate.session)
    queries = ["", "severity:high", "host:www.example.com severity:critical"]
    counted = await software.counts(scan, queries)
    for query in queries:
        found = await software.search(scan, SoftwareFilter(q=query, limit=1))
        assert counted.counts[query] == found.total, query
    queries = ["", "state:exposed", "kind:jwt or state:public"]
    counted = await secrets.counts(scan, queries)
    for query in queries:
        found = await secrets.search(scan, SecretFilter(q=query, limit=1))
        assert counted.counts[query] == found.total, query


async def test_an_address_names_as_many_web_assets_as_its_link_opens(estate, now):
    scan = await _rich_scan(estate, now)
    await estate.assets("run", ["10.0.0.2"], at=now, ip="10.0.0.2", port=80)
    addresses = await IpAddressService(estate.session).search(
        scan, IpGroupFilter(q="ip=10.0.0.2", limit=5)
    )
    (address,) = addresses.items
    opened = await SubdomainService(estate.session).search(
        estate.project_id, scan, SubdomainFilter(q="ip:10.0.0.2", limit=1)
    )
    assert address.host_count == opened.total == 2
    assert "10.0.0.2" not in address.hosts
