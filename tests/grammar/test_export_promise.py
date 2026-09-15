from __future__ import annotations

import tempfile
from datetime import timedelta
from pathlib import Path

import pytest
import sqlalchemy as sa

from app.services.endpoint import EndpointService
from app.services.ip_address import IpAddressService
from app.services.port import PortService
from app.services.subdomain import SubdomainService
from app.services.vulnerability import VulnerabilityService
from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import EndpointFilter
from shared.models.scan_correlation import IpGroupFilter, ServiceFilter
from shared.models.subdomain import Subdomain, SubdomainFilter
from shared.models.vulnerability import VulnerabilityFilter
from shared.services.asset_export import runner
from shared.services.asset_query import QueryScope
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.grammar


async def _seed(estate, now):
    old = now - timedelta(days=7)
    await estate.scan("example.com", "first", at=old)
    await estate.hosts("first", ["www.example.com"], at=old)

    await estate.scan("example.com", "run", at=now)
    await estate.hosts(
        "run",
        ["www.example.com", "api.example.com"],
        at=now,
        ips=["10.0.0.1"],
        status=200,
        title="Welcome",
        tech=["nginx"],
    )
    await estate.hosts(
        "run", ["dead.example.com"], at=now, ips=["10.0.0.2"], status=404, title="Gone"
    )
    await estate.assets("run", ["www.example.com"], at=now, ip="10.0.0.1")
    await estate.endpoints(
        "run", ["https://www.example.com/a", "https://www.example.com/b"], at=now
    )
    await estate.ports(
        "run", [("10.0.0.1", 443, "https"), ("10.0.0.2", 22, "ssh")], at=now
    )
    await estate.vulns("run", [("CVE-2021-1", "high")], at=now)
    await estate.session.commit()


async def _export_rows(estate, dimension: str, filters: dict) -> int:
    scope = QueryScope((estate.scans["run"],), project_id=estate.project_id)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "rows.csv"
        result = await estate.session.run_sync(
            lambda s: runner.run(
                s,
                dimension=dimension,
                scope=scope,
                filters=filters,
                now=utc_now(),
                export_format="csv",
                path=path,
                project_id=estate.project_id,
            )
        )
    return result.rows


@pytest.mark.parametrize(
    ("dimension", "filters"),
    [
        (SurfaceDimension.WEB_ASSETS.value, {}),
        (SurfaceDimension.WEB_ASSETS.value, {"q": "status:200"}),
        (SurfaceDimension.WEB_ASSETS.value, {"statuses": ["4xx"]}),
        (SurfaceDimension.ENDPOINTS.value, {}),
        (SurfaceDimension.SERVICES.value, {}),
        (SurfaceDimension.IPS.value, {}),
        (SurfaceDimension.VULNERABILITIES.value, {}),
    ],
)
async def test_an_export_writes_the_rows_the_table_shows(
    durable_estate, now, dimension, filters
):
    estate = durable_estate
    await _seed(estate, now)
    scope = QueryScope((estate.scans["run"],), project_id=estate.project_id)

    if dimension == SurfaceDimension.WEB_ASSETS.value:
        page = await SubdomainService(estate.session).search(
            estate.project_id, scope, SubdomainFilter(**filters)
        )
    elif dimension == SurfaceDimension.ENDPOINTS.value:
        page = await EndpointService(estate.session).search(
            scope, EndpointFilter(**filters)
        )
    elif dimension == SurfaceDimension.SERVICES.value:
        page = await PortService(estate.session).search(scope, ServiceFilter(**filters))
    elif dimension == SurfaceDimension.IPS.value:
        page = await IpAddressService(estate.session).search(
            scope, IpGroupFilter(**filters)
        )
    else:
        page = await VulnerabilityService(estate.session).search(
            scope, VulnerabilityFilter(**filters)
        )

    assert await _export_rows(estate, dimension, filters) == page.total


async def test_an_export_of_a_selection_writes_only_the_chosen_rows(
    durable_estate, now
):
    estate = durable_estate
    await _seed(estate, now)
    chosen = (
        await estate.session.scalars(
            sa.select(Subdomain.id)
            .where(Subdomain.scan_id == estate.scans["run"])
            .order_by(Subdomain.name)
            .limit(2)
        )
    ).all()

    assert (
        await _export_rows(estate, "web_assets", {"ids": [str(i) for i in chosen]}) == 2
    )


async def test_a_filter_that_matches_nothing_exports_nothing(durable_estate, now):
    estate = durable_estate
    await _seed(estate, now)

    assert await _export_rows(estate, "web_assets", {"q": "status:418"}) == 0
