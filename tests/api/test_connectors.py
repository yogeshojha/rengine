from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.services.connector import ConnectorError, ConnectorService
from connectors import handoff
from connectors.notice import notices_for
from shared.definitions.connectors import (
    ACTION_KIND_LABELS,
    SEVERITY_HIGHLIGHT,
    ActionKind,
    CandidateState,
    NoticeKind,
)
from shared.definitions.endpoints import EndpointSource, shape_for
from shared.definitions.vulnerabilities import Protocol
from shared.enums.scan import ScanActivityStatus
from shared.models.connector import (
    ConnectorAction,
    ConnectorCandidate,
    ConnectorCreate,
    FindingReport,
    HandoffRequest,
    IngestItem,
    IngestRequest,
)
from shared.models.endpoint import Endpoint, EndpointResponse
from shared.models.scan import Scan
from shared.models.vulnerability import Vulnerability
from shared.services import proxy_sync
from shared.services.scan_resolve import MASK, redact_message, seal_headers

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


# ---------- hand-off ----------


def _finding(**kw) -> Vulnerability:
    base = {
        "project_id": uuid.uuid4(),
        "scan_id": uuid.uuid4(),
        "target_id": uuid.uuid4(),
        "fingerprint": "f",
        "template_id": "CVE-2021-44228",
        "template_name": "Apache Log4j RCE",
        "severity": "critical",
        "protocol": Protocol.HTTP.value,
        "matched_at": f"https://{HOST}/api",
        "url": f"https://{HOST}/api",
        "cve_ids": ["CVE-2021-44228"],
    }
    return Vulnerability(**{**base, **kw})


def test_finding_handoff_carries_the_request_response_and_note():
    out = handoff.from_finding(
        _finding(
            request='POST /api HTTP/1.1\nHost: app.example.com\nX-Api-Version: 2\n\n{"a":1}',
            response="HTTP/1.1 200 OK\nContent-Type: text/plain\n\nok",
        ),
        link="http://ui/scans/x",
    )
    assert out.method == "POST"
    assert out.request.startswith("POST /api HTTP/1.1\r\nHost: app.example.com\r\n")
    assert out.request.endswith('\r\n\r\n{"a":1}')
    assert out.response == (
        "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nok"
    )
    assert out.notes.split("\n") == [
        "reNgine · Critical · CVE-2021-44228",
        "Apache Log4j RCE",
        "CVE-2021-44228",
        f"https://{HOST}/api",
        "http://ui/scans/x",
    ]
    assert out.color == SEVERITY_HIGHLIGHT["critical"]
    assert out.label == "CVE-2021-44228"


def test_finding_without_an_http_exchange_is_not_handed_off():
    assert (
        handoff.from_finding(
            _finding(protocol=Protocol.DNS.value, matched_at=HOST, url=None)
        )
        is None
    )
    built = handoff.from_finding(_finding(request=None))
    assert built.request.startswith(f"GET /api HTTP/1.1\r\nHost: {HOST}\r\n")


def test_endpoint_handoff_builds_a_form_body_for_post():
    endpoint = Endpoint(
        project_id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        signature="s",
        url=f"https://{HOST}:8443/login?from=/",
        host=HOST,
        port=8443,
        path="/login",
        dir_path="/",
        methods=["POST"],
        params=["from", "user", "pass word"],
        param_samples=[{"from": "/", "user": "admin"}],
        status_code=302,
        sources=["katana"],
    )
    out = handoff.from_endpoint(endpoint)
    head, _, body = out.request.partition("\r\n\r\n")
    lines = head.split("\r\n")
    assert lines[0] == "POST /login?from=/ HTTP/1.1"
    assert lines[1] == f"Host: {HOST}:8443"
    assert "Content-Type: application/x-www-form-urlencoded" in lines
    assert body == "user=admin&pass%20word="
    assert f"Content-Length: {len(body)}" in lines
    assert out.response is None
    assert out.label == "/login"


def test_endpoint_handoff_attaches_the_stored_response():
    endpoint = Endpoint(
        project_id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        signature="s",
        url=f"https://{HOST}/robots.txt",
        host=HOST,
        path="/robots.txt",
        dir_path="/",
        methods=["GET"],
    )
    stored = EndpointResponse(
        endpoint_id=endpoint.id,
        scan_id=endpoint.scan_id,
        raw_response_header="HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n",
        response_body="User-agent: *\n",
    )
    out = handoff.from_endpoint(endpoint, stored)
    assert out.request.startswith("GET /robots.txt HTTP/1.1\r\n")
    assert out.response == (
        "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 14\r\n\r\n"
        "User-agent: *\n"
    )


def test_a_decoded_body_drops_the_transfer_headers():
    out = handoff.response_text(
        "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\nContent-Encoding: gzip\r\n"
        "Content-Length: 999\r\nContent-Type: text/html\r\n",
        "<html>é</html>",
    )
    head, _, body = out.partition("\r\n\r\n")
    assert "Transfer-Encoding" not in head
    assert "Content-Encoding" not in head
    assert head.count("Content-Length") == 1
    assert f"Content-Length: {len(body.encode())}" in head


def test_restore_headers_fills_masked_values_from_the_run_alone():
    request = (
        f"GET /a HTTP/1.1\r\nHost: {HOST}\r\nAuthorization: Bearer {MASK}\r\n"
        f"Cookie: {MASK}\r\nX-Other: {MASK}\r\n\r\n"
    )
    out = handoff.restore_headers(
        request, {"Authorization": "Bearer real-token", "cookie": "sid=1"}
    )
    assert "Authorization: Bearer real-token" in out
    assert "Cookie: sid=1" in out
    assert f"X-Other: {MASK}" in out, "a header the run did not send stays masked"
    assert handoff.restore_headers(request, {}) == request


async def test_handoff_queues_requests_and_delivers_them_once(estate, now):
    await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.endpoints("census", ["/a", "/b"], at=now, host=HOST, status=200)
    await estate.vulns("census", [("cve-x", "high")], at=now, host=HOST)
    service, row = await _connector(estate)
    endpoints = await _endpoints(estate.session, estate.scans["census"])
    finding = await estate.session.scalar(
        select(Vulnerability).where(Vulnerability.scan_id == estate.scans["census"])
    )
    finding.protocol = Protocol.HTTP.value
    await estate.session.flush()

    result = await service.handoff(
        row.id,
        estate.project_id,
        HandoffRequest(
            kind=ActionKind.ORGANIZER.value,
            endpoint_ids=[endpoints["/a"].id],
            finding_ids=[finding.id],
        ),
    )
    assert result.queued == 2
    assert result.skipped == 0
    assert result.tool == ACTION_KIND_LABELS[ActionKind.ORGANIZER.value]

    delivered = await service.take_actions(row)
    assert {a.kind for a in delivered} == {ActionKind.ORGANIZER.value}
    by_url = {a.url: a for a in delivered}
    assert by_url[f"https://{HOST}/a"].request.startswith("GET /a HTTP/1.1\r\n")
    assert by_url[f"https://{HOST}/"].notes.startswith("reNgine · High · cve-x")
    assert by_url[f"https://{HOST}/"].color == SEVERITY_HIGHLIGHT["high"]
    assert await service.take_actions(row) == []


async def test_handoff_refuses_an_unknown_tool_and_an_empty_pick(estate, now):
    service, row = await _connector(estate)
    with pytest.raises(ConnectorError):
        await service.handoff(row.id, estate.project_id, HandoffRequest(kind="scanner"))
    with pytest.raises(ConnectorError):
        await service.handoff(row.id, estate.project_id, HandoffRequest())


async def test_delivery_restores_the_run_credentials_only_when_asked(estate, now):
    await estate.scan(
        "example.com",
        "census",
        at=now - timedelta(hours=1),
        config={"headers": seal_headers({"Authorization": "Bearer real-token"})},
    )
    await estate.vulns("census", [("cve-x", "high")], at=now, host=HOST)
    finding = await estate.session.scalar(
        select(Vulnerability).where(Vulnerability.scan_id == estate.scans["census"])
    )
    finding.request = (
        f"GET / HTTP/1.1\r\nHost: {HOST}\r\nAuthorization: Bearer {MASK}\r\n\r\n"
    )
    await estate.session.flush()
    service, row = await _connector(estate)

    await service.handoff(
        row.id, estate.project_id, HandoffRequest(finding_ids=[finding.id])
    )
    (masked,) = await service.take_actions(row)
    assert f"Authorization: Bearer {MASK}" in masked.request

    row.restore_credentials = True
    await service.handoff(
        row.id, estate.project_id, HandoffRequest(finding_ids=[finding.id])
    )
    (restored,) = await service.take_actions(row)
    assert "Authorization: Bearer real-token" in restored.request
    stored = await estate.session.scalar(select(ConnectorAction.request))
    assert "real-token" not in stored, "the queue row keeps the masked text"


# ---------- hand-off across content types ----------


def _candidate(**kw) -> ConnectorCandidate:
    base = {
        "connector_id": uuid.uuid4(),
        "project_id": uuid.uuid4(),
        "signature": "s",
        "url": f"https://{HOST}/api/orders?page=1",
        "scheme": "https",
        "host": HOST,
        "path": "/api/orders",
        "dir_path": "/api/",
        "methods": ["POST"],
        "params": ["page", "amount", "note"],
        "source_tool": "proxy",
    }
    return ConnectorCandidate(**{**base, **kw})


def test_a_json_sample_gets_a_json_body_template():
    out = handoff.from_candidate(
        _candidate(
            request_sample=(
                f"POST /api/orders?page=1 HTTP/1.1\r\nHost: {HOST}\r\n"
                "Content-Type: application/json\r\nContent-Length: 87\r\n\r\n"
            )
        )
    )
    head, _, body = out.request.partition("\r\n\r\n")
    assert out.method == "POST"
    assert body == '{"amount": "", "note": ""}', "query names stay out of the body"
    assert f"Content-Length: {len(body)}" in head
    assert head.count("Content-Length") == 1
    assert "Content-Type: application/json" in head


def test_a_multipart_sample_gets_a_multipart_body_with_its_own_boundary():
    out = handoff.from_candidate(
        _candidate(
            request_sample=(
                f"POST /api/orders?page=1 HTTP/1.1\r\nHost: {HOST}\r\n"
                "Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryX\r\n\r\n"
            )
        )
    )
    head, _, body = out.request.partition("\r\n\r\n")
    boundary = head.split("boundary=", 1)[1].split("\r\n", 1)[0]
    assert boundary != "----WebKitFormBoundaryX"
    assert body.startswith(
        f'--{boundary}\r\nContent-Disposition: form-data; name="amount"'
    )
    assert body.endswith(f"--{boundary}--\r\n")
    assert head.count("Content-Type") == 1


def test_an_xml_sample_gets_an_xml_body():
    out = handoff.from_candidate(
        _candidate(
            request_sample=(
                f"PUT /api/orders HTTP/1.1\r\nHost: {HOST}\r\nContent-Type: text/xml\r\n\r\n"
            ),
            url=f"https://{HOST}/api/orders",
            params=["amount"],
        )
    )
    body = out.request.partition("\r\n\r\n")[2]
    assert body.startswith('<?xml version="1.0" encoding="UTF-8"?><request><amount>')


def test_a_sample_with_no_parameters_ships_an_empty_body_and_says_so():
    out = handoff.from_candidate(
        _candidate(
            request_sample=(
                f"POST /api/orders HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: 40\r\n\r\n"
            ),
            params=[],
        )
    )
    head, _, body = out.request.partition("\r\n\r\n")
    assert body == ""
    assert "Content-Length: 0" in head


def test_a_get_sample_gets_no_body():
    out = handoff.from_candidate(
        _candidate(
            request_sample=f"GET /api/orders?page=1 HTTP/1.1\r\nHost: {HOST}\r\n\r\n",
            methods=["GET"],
        )
    )
    assert out.request == f"GET /api/orders?page=1 HTTP/1.1\r\nHost: {HOST}\r\n\r\n"


def test_a_stored_request_body_keeps_its_length_after_the_cut():
    long_body = "a" * (handoff.MAX_HANDOFF_REQUEST * 2)
    out = handoff.request_message(
        f"POST /x HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: {len(long_body)}\r\n\r\n"
        + long_body
    )
    head, _, body = out.partition("\r\n\r\n")
    assert len(out) <= handoff.MAX_HANDOFF_REQUEST
    assert len(body) < len(long_body)
    assert f"Content-Length: {len(body)}" in head


def test_a_declared_charset_becomes_the_utf8_the_body_is_in():
    out = handoff.response_text(
        'HTTP/1.1 200 OK\r\nContent-Type: text/html; charset="ISO-8859-1"\r\n',
        "<p>café</p>",
    )
    head, _, body = out.partition("\r\n\r\n")
    assert "Content-Type: text/html; charset=utf-8" in head
    assert f"Content-Length: {len(body.encode())}" in head
    assert len(body.encode()) == len(body) + 1


def test_a_binary_response_ships_its_headers_alone():
    out = handoff.response_text(
        "HTTP/1.1 200 OK\r\nContent-Type: image/png\r\nContent-Length: 4821\r\n", None
    )
    assert (
        out == "HTTP/1.1 200 OK\r\nContent-Type: image/png\r\nContent-Length: 0\r\n\r\n"
    )


def test_request_targets_are_percent_encoded_once():
    assert (
        handoff.request_target("https://h/a b/ç?q=x y&r=%20")
        == "/a%20b/%C3%A7?q=x%20y&r=%20"
    )
    assert handoff.request_target("https://h") == "/"


def test_head_and_ipv6_requests():
    endpoint = Endpoint(
        project_id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        signature="s",
        url="http://[2001:db8::1]:8080/status",
        host="2001:db8::1",
        port=8080,
        path="/status",
        dir_path="/",
        methods=["HEAD"],
        params=["x"],
    )
    out = handoff.from_endpoint(endpoint)
    head, _, body = out.request.partition("\r\n\r\n")
    assert head.startswith("HEAD /status HTTP/1.1\r\nHost: [2001:db8::1]:8080\r\n")
    assert body == ""
    assert "Content-Length" not in head
