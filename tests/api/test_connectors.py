from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.services.connector import ConnectorService
from connectors.notice import notices_for
from shared.definitions.connectors import CandidateState, NoticeKind
from shared.definitions.endpoints import EndpointSource, shape_for
from shared.enums.scan import ScanActivityStatus
from shared.models.connector import (
    ConnectorCandidate,
    ConnectorCreate,
    FindingReport,
    IngestItem,
    IngestRequest,
)
from shared.models.endpoint import Endpoint
from shared.models.scan import Scan
from shared.models.vulnerability import Vulnerability
from shared.services import proxy_sync
from shared.services.scan_resolve import MASK, redact_message

pytestmark = pytest.mark.api

HOST = "app.example.com"


def _item(url: str, **kw) -> IngestItem:
    return IngestItem(url=url, status_code=kw.pop("status", 200), **kw)


async def _connector(estate, name: str = "Burp"):
    service = ConnectorService(estate.session)
    created = await service.create(
        ConnectorCreate(name=name, project_id=estate.project_id), estate.user_id
    )
    row = await service.get(created.connector.id, estate.project_id)
    return service, row


async def _candidates(session, connector_id) -> dict[str, ConnectorCandidate]:
    rows = (
        (
            await session.execute(
                select(ConnectorCandidate).where(
                    ConnectorCandidate.connector_id == connector_id
                )
            )
        )
        .scalars()
        .all()
    )
    return {r.path: r for r in rows}


async def _endpoints(session, scan_id) -> dict[str, Endpoint]:
    rows = (
        (await session.execute(select(Endpoint).where(Endpoint.scan_id == scan_id)))
        .scalars()
        .all()
    )
    return {r.path: r for r in rows}


# ---------- shape ----------


def test_shape_collapses_identifiers():
    assert shape_for("/api/users/1234")[0] == "/api/users/{id}"
    assert shape_for("/api/users/1234/orders")[0] == "/api/users/{id}/orders"
    assert shape_for("/assets/app-3f9a1c2b.js")[0] == "/assets/app-{id}.js"
    assert shape_for("/artists.php")[0] == "/artists.php"
    assert shape_for("/")[0] == "/"


def test_shape_keeps_a_trailing_slash():
    assert shape_for("/product/9999/")[0] == "/product/{id}/"


# ---------- notices ----------


def test_unseen_needs_a_covering_scan():
    kwargs = {"interests": [], "methods": ["GET"], "status_code": 200}
    assert NoticeKind.UNSEEN_BY_SCANS.value not in notices_for(
        known=False, covered=False, **kwargs
    )
    assert NoticeKind.UNSEEN_BY_SCANS.value in notices_for(
        known=False, covered=True, **kwargs
    )
    assert NoticeKind.NEW_PARAMS.value in notices_for(
        known=True, covered=True, new_params=True, **kwargs
    )


# ---------- known and coverage ----------


async def test_known_matches_on_host_and_shape(estate, now):
    await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.endpoints(
        "census", ["/artists.php", "/api/users/1042"], at=now, host=HOST
    )
    await estate.session.execute(
        Endpoint.__table__.update().values(shape=Endpoint.path)
    )
    await estate.session.execute(
        Endpoint.__table__.update()
        .where(Endpoint.path == "/api/users/1042")
        .values(shape="/api/users/{id}")
    )
    service, row = await _connector(estate)

    out = await service.ingest(
        row,
        IngestRequest(
            items=[
                _item(f"https://{HOST}/artists.php?artist=1"),
                _item(f"https://{HOST}/api/users/2000", authenticated=True),
                _item(f"https://{HOST}/secret/backup.sql"),
            ]
        ),
    )
    rows = await _candidates(estate.session, row.id)

    assert out.accepted == 3
    assert rows["/artists.php"].known, "same path, different param set is still known"
    assert NoticeKind.NEW_PARAMS.value in rows["/artists.php"].notices
    assert rows["/api/users/{id}"].known, "an id-bearing path matches by shape"
    assert not rows["/secret/backup.sql"].known
    assert NoticeKind.UNSEEN_BY_SCANS.value in rows["/secret/backup.sql"].notices


async def test_browsing_does_not_make_itself_known(estate, now):
    await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.endpoints("census", ["/login.php"], at=now, host=HOST)
    await estate.session.execute(
        Endpoint.__table__.update().values(shape=Endpoint.path)
    )
    service, row = await _connector(estate)

    await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/api/u/1")]))
    await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/api/u/2")]))
    rows = await _candidates(estate.session, row.id)

    assert not rows["/api/u/{id}"].known, "a proxy-only endpoint row is not a scan"
    assert NoticeKind.UNSEEN_BY_SCANS.value in rows["/api/u/{id}"].notices


async def test_unseen_is_not_claimed_for_an_unscanned_target(estate, now):
    await estate.target("example.com")
    service, row = await _connector(estate)

    await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/admin/")]))
    rows = await _candidates(estate.session, row.id)

    assert not rows["/admin/"].known
    assert NoticeKind.UNSEEN_BY_SCANS.value not in rows["/admin/"].notices
    assert NoticeKind.ADMIN.value in rows["/admin/"].notices


# ---------- the sitemap lands ----------


async def test_browsing_joins_the_covering_scan_as_proxy_endpoints(estate, now):
    scan_id = await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.endpoints("census", ["/login.php"], at=now, host=HOST)
    await estate.session.execute(
        Endpoint.__table__.update().values(shape=Endpoint.path)
    )
    service, row = await _connector(estate)

    out = await service.ingest(
        row,
        IngestRequest(
            items=[
                _item(f"https://{HOST}/login.php", method="POST", body_params=["u"]),
                _item(f"https://{HOST}/dashboard", authenticated=True, title="Home"),
            ]
        ),
    )
    endpoints = await _endpoints(estate.session, scan_id)

    assert out.recorded == 2
    assert endpoints["/dashboard"].primary_source == EndpointSource.PROXY.value
    assert endpoints["/dashboard"].shape == "/dashboard"
    assert endpoints["/dashboard"].is_probed
    assert endpoints["/dashboard"].status_code == 200
    assert "/login.php" in endpoints, "the scanner's own row is kept"


async def test_an_unscanned_target_gets_a_browsing_run(estate, now):
    target_id = await estate.target("example.com")
    service, row = await _connector(estate)

    out = await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/")]))

    run = await estate.session.scalar(
        select(Scan).where(Scan.target_id == target_id, Scan.scope == "full")
    )
    assert out.recorded == 1
    assert run is not None
    assert run.engine_name.startswith("Browsing")
    assert (await _endpoints(estate.session, run.id))["/"].sources == [
        EndpointSource.PROXY.value
    ]


async def test_a_running_census_scan_defers_to_finalize(estate, now):
    scan_id = await estate.scan("example.com", "live", at=now, status="running")
    service, row = await _connector(estate)

    out = await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/x")]))
    assert out.recorded == 0
    assert not await _endpoints(estate.session, scan_id)

    await estate.activity("live", {"url_discovery": ScanActivityStatus.SUCCESS.value})
    scan = await estate.session.get(Scan, scan_id)
    replayed = await estate.session.run_sync(proxy_sync.replay, scan)

    assert replayed is not None
    assert replayed.created == 1
    assert (await _endpoints(estate.session, scan_id))["/x"].primary_source == "proxy"


# ---------- attaching ----------


async def test_shapes_recorded_before_the_target_existed_attach_later(estate, now):
    service, row = await _connector(estate)
    await service.ingest(row, IngestRequest(items=[_item(f"https://{HOST}/orphan")]))
    assert (await _candidates(estate.session, row.id))["/orphan"].target_id is None

    target_id = await estate.target("example.com")
    attached = await service.attach_targets(row)

    rows = await _candidates(estate.session, row.id)
    assert attached == {target_id}
    assert rows["/orphan"].target_id == target_id


# ---------- scanning the queue ----------


async def test_scan_launches_one_run_per_target_and_stamps_only_its_rows(
    estate, now, monkeypatch
):
    a = await estate.target("example.com")
    b = await estate.target("other.test")
    service, row = await _connector(estate)
    await service.ingest(
        row,
        IngestRequest(
            items=[_item("https://x.example.com/a"), _item("https://y.other.test/b")]
        ),
    )
    launched: list[tuple[uuid.UUID, list[str]]] = []

    class _FakeScanService:
        def __init__(self, session):
            pass

        async def create(self, data, project_id, created_by):
            scan = Scan(
                project_id=project_id,
                target_id=data.target_id,
                engine_name="Rescan",
                execution_config={},
                created_by=created_by,
            )
            estate.session.add(scan)
            await estate.session.flush()
            launched.append((data.target_id, [s.value for s in data.seed_assets]))
            return scan

    monkeypatch.setattr("app.services.scan.ScanService", _FakeScanService)
    scans = await service.scan(row.id, estate.project_id, estate.user_id)
    rows = await _candidates(estate.session, row.id)

    assert len(scans) == 2
    assert {t for t, _ in launched} == {a, b}
    assert rows["/a"].scan_id == next(s.id for s in scans if s.target_id == a)
    assert rows["/b"].scan_id == next(s.id for s in scans if s.target_id == b)
    assert rows["/a"].state == CandidateState.QUEUED.value

    settled = await estate.session.run_sync(proxy_sync.settle_queue, scans[0])
    assert settled == 1


# ---------- findings ----------


def test_redact_message_masks_credential_headers():
    raw = "GET /a HTTP/1.1\r\nHost: x\r\nCookie: session=abc\r\nAuthorization: Bearer t\r\n\r\nsession=abc"
    out = redact_message(raw)
    assert f"Cookie: {MASK}" in out
    assert f"Authorization: {MASK}" in out
    assert out.endswith("session=abc"), "the body is not a header"


async def test_reported_findings_store_a_redacted_request(estate, now):
    await estate.target("example.com")
    service, row = await _connector(estate)

    out = await service.record_finding(
        row,
        FindingReport(
            title="IDOR on orders",
            url=f"https://{HOST}/api/orders/1",
            severity="high",
            request="GET /api/orders/1 HTTP/1.1\r\nCookie: sid=secret\r\n\r\n",
        ),
        estate.user_id,
    )
    finding = await estate.session.get(Vulnerability, out.finding_id)

    assert "secret" not in finding.request
    assert MASK in finding.request
