from __future__ import annotations

import pytest
import sqlalchemy as sa
from fastapi import HTTPException

from app.services.surface_delete import SurfaceDeleteService
from shared.definitions.surface import SurfaceDimension
from shared.models.http_asset import HttpAsset
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
            **estate.row_ids("run"),
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
    ids = estate.row_ids("run")
    secret = Secret(
        **ids,
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
            **ids,
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
            .where(SecretSighting.scan_id == ids["scan_id"])
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
