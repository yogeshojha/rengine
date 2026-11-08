from __future__ import annotations

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from app.services.surface_delete import SurfaceDeleteService
from shared.definitions.surface import SurfaceDimension
from shared.models.endpoint import Endpoint, EndpointResponse
from shared.models.http_asset import HttpAsset
from shared.models.interest import InterestSignal
from shared.models.secret import Secret, SecretSighting
from shared.models.subdomain import Subdomain
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import QueryScope

pytestmark = pytest.mark.api


async def _seed(estate, now):
    await estate.scan("example.com", "run", at=now)
    await estate.scan("example.com", "other", at=now)
    await estate.hosts("run", ["www.example.com", "api.example.com"], at=now)
    await estate.hosts("other", ["www.example.com"], at=now)
    await estate.assets("run", ["www.example.com"], at=now, port=443)
    await estate.assets("run", ["www.example.com"], at=now, port=80)
    await estate.assets("run", ["api.example.com"], at=now)
    await estate.vulns("run", [("weak-tls-a", "low"), ("weak-tls-b", "low")], at=now)
    await estate.session.flush()


def _scope(estate, name: str) -> QueryScope:
    return QueryScope((estate.scans[name],), project_id=estate.project_id)


async def _host_id(estate, scan: str, name: str):
    return await estate.session.scalar(
        sa.select(Subdomain.id).where(
            Subdomain.scan_id == estate.scans[scan], Subdomain.name == name
        )
    )


async def test_a_deleted_web_asset_takes_its_stored_responses(estate, now):
    await _seed(estate, now)
    doomed = await _host_id(estate, "run", "www.example.com")

    result = await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"), SurfaceDimension.WEB_ASSETS.value, [str(doomed)]
    )

    assert result.deleted == 1
    assert result.related == {"http_assets": 2}
    left = await estate.session.scalar(
        sa.select(sa.func.count()).select_from(
            sa.select(HttpAsset.id)
            .where(HttpAsset.scan_id == estate.scans["run"])
            .subquery()
        )
    )
    assert left == 1


async def _count(estate, model, *where) -> int:
    return await estate.session.scalar(
        sa.select(sa.func.count()).select_from(model).where(*where)
    )


async def test_a_deleted_web_asset_takes_its_interest_signals(estate, now):
    await _seed(estate, now)
    scan_id = estate.scans["run"]
    doomed = await _host_id(estate, "run", "www.example.com")
    kept = await _host_id(estate, "run", "api.example.com")
    for host_id, host in ((doomed, "www.example.com"), (kept, "api.example.com")):
        estate.session.add(
            InterestSignal(
                scan_id=scan_id,
                target_id=await estate._target_of(scan_id),
                project_id=estate.project_id,
                subdomain_id=host_id,
                host=host,
                source="rule",
                key="admin-panel",
                kind="admin",
            )
        )
    await estate.session.flush()

    await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"), SurfaceDimension.WEB_ASSETS.value, [str(doomed)]
    )

    assert (
        await _count(estate, InterestSignal, InterestSignal.subdomain_id == doomed) == 0
    )
    assert (
        await _count(estate, InterestSignal, InterestSignal.subdomain_id == kept) == 1
    )


async def test_a_deleted_endpoint_takes_its_stored_response(estate, now):
    await _seed(estate, now)
    scan_id = estate.scans["run"]
    await estate.endpoints("run", ["/login", "/about"], at=now, status=200)
    rows = (
        await estate.session.execute(
            sa.select(Endpoint.id, Endpoint.path).where(Endpoint.scan_id == scan_id)
        )
    ).all()
    ids = {row.path: row.id for row in rows}
    for endpoint_id in ids.values():
        estate.session.add(
            EndpointResponse(
                endpoint_id=endpoint_id, scan_id=scan_id, response_body="<html>"
            )
        )
    await estate.session.flush()

    result = await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"), SurfaceDimension.ENDPOINTS.value, [str(ids["/login"])]
    )

    assert result.deleted == 1
    left = await estate.session.scalars(sa.select(EndpointResponse.endpoint_id))
    assert set(left.all()) == {ids["/about"]}


async def test_a_row_outside_the_scope_is_not_deleted(estate, now):
    await _seed(estate, now)
    doomed = await _host_id(estate, "other", "www.example.com")

    result = await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"), SurfaceDimension.WEB_ASSETS.value, [str(doomed)]
    )

    assert result.deleted == 0
    assert await estate.session.get(Subdomain, doomed) is not None


async def test_an_issue_deletes_every_finding_of_that_check(estate, now):
    await _seed(estate, now)
    scan_id = estate.scans["run"]
    estate.session.add(
        Vulnerability(
            project_id=estate.project_id,
            scan_id=scan_id,
            target_id=await estate._target_of(scan_id),
            fingerprint="weak-tls-a-2",
            template_id="weak-tls-a",
            template_name="Weak Tls A",
            severity="low",
            matched_at="https://api.example.com/",
            host="api.example.com",
            discovered_at=now,
        )
    )
    await estate.session.flush()

    result = await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"),
        SurfaceDimension.VULNERABILITIES.value,
        ["weak-tls-a"],
        key="template_id",
    )

    assert result.deleted == 2
    left = await estate.session.scalars(
        sa.select(Vulnerability.template_id).where(Vulnerability.scan_id == scan_id)
    )
    assert set(left.all()) == {"weak-tls-b"}


async def test_a_deleted_secret_takes_its_sightings(estate, now):
    await _seed(estate, now)
    scan_id = estate.scans["run"]
    target_id = await estate._target_of(scan_id)
    secret = Secret(
        project_id=estate.project_id,
        scan_id=scan_id,
        target_id=target_id,
        fingerprint="f" * 8,
        kind="google_api_key",
        group="cloud",
        value="AIza-test",
        host="www.example.com",
        url="https://www.example.com/",
        discovered_at=now,
    )
    estate.session.add(secret)
    await estate.session.flush()
    estate.session.add(
        SecretSighting(
            secret_id=secret.id,
            scan_id=scan_id,
            target_id=target_id,
            project_id=estate.project_id,
            host="www.example.com",
            url="https://www.example.com/app.js",
        )
    )
    await estate.session.flush()

    result = await SurfaceDeleteService(estate.session).delete(
        _scope(estate, "run"), SurfaceDimension.SECRETS.value, [str(secret.id)]
    )

    assert result.deleted == 1
    left = await estate.session.scalar(
        sa.select(sa.func.count()).select_from(
            sa.select(SecretSighting.id)
            .where(SecretSighting.scan_id == scan_id)
            .subquery()
        )
    )
    assert left == 0


async def test_an_unknown_key_is_refused(estate, now):
    await _seed(estate, now)

    with pytest.raises(HTTPException) as raised:
        await SurfaceDeleteService(estate.session).delete(
            _scope(estate, "run"),
            SurfaceDimension.SECRETS.value,
            ["x"],
            key="value",
        )

    assert raised.value.status_code == 422


async def test_an_unknown_dimension_is_refused(estate, now):
    await _seed(estate, now)

    with pytest.raises(HTTPException) as raised:
        await SurfaceDeleteService(estate.session).delete(
            _scope(estate, "run"), "nope", ["x"]
        )

    assert raised.value.status_code == 422
