from __future__ import annotations

import re
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.services.connector import ConnectorService, HandoffError
from connectors import base, handoff
from connectors.burp.connector import BurpConnector
from shared.definitions.connectors import MAX_HANDOFF_REQUEST, ActionKind
from shared.definitions.vulnerabilities import Protocol
from shared.models.connector import ConnectorAction, ConnectorCreate, HandoffRequest
from shared.models.endpoint import EndpointFilter
from shared.models.http_asset import HttpAsset
from shared.models.vulnerability import Vulnerability
from shared.services.scan_resolve import MASK, seal_headers

pytestmark = pytest.mark.api

HOST = "app.example.com"


async def _connector(estate):
    service = ConnectorService(estate.session)
    created = await service.create(
        ConnectorCreate(name="Burp", project_id=estate.project_id), estate.user_id
    )
    return service, await service.get(created.connector.id, estate.project_id)


async def _findings(
    estate, now, *, request: str | None, config: dict | None = None, count: int = 1
) -> list[Vulnerability]:
    await estate.scan(
        "example.com", "census", at=now - timedelta(hours=1), config=config
    )
    await estate.vulns(
        "census", [(f"cve-{n}", "high") for n in range(count)], at=now, host=HOST
    )
    rows = (
        (
            await estate.session.execute(
                select(Vulnerability)
                .where(Vulnerability.scan_id == estate.scans["census"])
                .order_by(Vulnerability.fingerprint)
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        row.protocol = Protocol.HTTP.value
        row.request = request
    await estate.session.flush()
    return list(rows)


# ---------- the edited request ----------


def test_an_edited_head_gets_crlf_and_the_body_its_own_length():
    out = handoff.edited_request(
        f'POST /api HTTP/1.1\nHost: {HOST}\nContent-Length: 1\nX-Test: 1\n\n{{"a":"é"}}'
    )
    head, _, body = out.partition("\r\n\r\n")
    assert body == '{"a":"é"}'
    assert head.split("\r\n") == [
        "POST /api HTTP/1.1",
        f"Host: {HOST}",
        f"Content-Length: {len(body.encode())}",
        "X-Test: 1",
    ], "the length is set where it stood"


def test_an_edited_body_without_a_length_gets_one():
    out = handoff.edited_request(f"POST /a HTTP/1.1\r\nHost: {HOST}\r\n\r\nx=1")
    assert out == f"POST /a HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: 3\r\n\r\nx=1"


def test_an_emptied_body_states_a_zero_length():
    out = handoff.edited_request(
        f"POST /a HTTP/1.1\nHost: {HOST}\nContent-Length: 12\n\n"
    )
    assert out == f"POST /a HTTP/1.1\r\nHost: {HOST}\r\nContent-Length: 0\r\n\r\n"


def test_an_edited_get_with_no_blank_line_gets_no_body():
    out = handoff.edited_request(f"\n\nGET / HTTP/1.1 \nHost: {HOST}\n")
    assert out == f"GET / HTTP/1.1\r\nHost: {HOST}\r\n\r\n"


def test_an_lf_head_splits_before_a_crlf_body():
    body = '--b\r\nContent-Disposition: form-data; name="a"\r\n\r\n1\r\n--b--\r\n'
    out = handoff.edited_request(
        f"POST /u HTTP/1.1\nHost: {HOST}\nContent-Type: multipart/form-data; boundary=b"
        f"\n\n{body}"
    )
    head, _, sent = out.partition("\r\n\r\n")
    assert sent == body
    assert f"Content-Length: {len(body)}" in head.split("\r\n")


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "The request is empty."),
        (" \n ", "The request is empty."),
        ("GET /\nHost: h\n\n", "The request line must read METHOD target HTTP/1.1."),
        ("GET  / HTTP/1.1\nHost: h\n\n", "The request line must read"),
        ("GET / HTTP/2\nHost: h\n\n", "The request line must read"),
        ("Host: h\n\nGET / HTTP/1.1", "The request line must read"),
        ("GET / HTTP/1.1\nAccept: */*\n\n", "The request has no Host header."),
        ("GET / HTTP/1.1\nHost:\n\n", "The request has no Host header."),
        ("GET / HTTP/1.1\nHost: h\n\na\x00b", "The request contains a NUL character."),
    ],
)
def test_an_edited_request_is_refused_with_its_reason(text, reason):
    with pytest.raises(handoff.RequestError, match=re.escape(reason)):
        handoff.edited_request(text)


def test_an_edited_request_over_the_cap_is_refused_not_cut():
    text = f"POST / HTTP/1.1\nHost: {HOST}\n\n" + "a" * MAX_HANDOFF_REQUEST
    with pytest.raises(handoff.RequestError, match="longer than"):
        handoff.edited_request(text)


# ---------- preview ----------


async def test_preview_is_the_request_the_send_queues(estate, now):
    (finding,) = await _findings(
        estate,
        now,
        request=f"GET /api HTTP/1.1\nHost: {HOST}\nAuthorization: Bearer {MASK}\n\n",
    )
    service, row = await _connector(estate)
    pick = HandoffRequest(finding_ids=[finding.id])

    preview = await service.preview(row.id, estate.project_id, pick)
    assert preview.url == f"https://{HOST}/"
    assert preview.request == (
        f"GET /api HTTP/1.1\r\nHost: {HOST}\r\nAuthorization: Bearer {MASK}\r\n\r\n"
    ), "masked values stay masked"

    await service.handoff(row.id, estate.project_id, pick)
    (sent,) = await service.take_actions(row)
    assert sent.request == preview.request


async def test_preview_of_a_web_asset_is_its_probe_request(estate, now):
    await estate.scan("example.com", "census", at=now - timedelta(hours=1))
    await estate.assets("census", [HOST], at=now)
    asset = await estate.session.scalar(
        select(HttpAsset).where(HttpAsset.scan_id == estate.scans["census"])
    )
    asset.raw_request = f"GET / HTTP/1.1\r\nHost: {HOST}\r\nUser-Agent: probe\r\n\r\n"
    await estate.session.flush()
    service, row = await _connector(estate)

    preview = await service.preview(
        row.id, estate.project_id, HandoffRequest(asset_ids=[asset.id])
    )
    assert preview.url == asset.url
    assert preview.request == asset.raw_request


async def test_preview_takes_exactly_one_row(estate, now):
    first, second = await _findings(estate, now, request=None, count=2)
    service, row = await _connector(estate)
    for pick in (
        HandoffRequest(finding_ids=[first.id, second.id]),
        HandoffRequest(),
        HandoffRequest(finding_ids=[first.id], filter=EndpointFilter()),
    ):
        with pytest.raises(HandoffError, match="Select exactly one row"):
            await service.preview(row.id, estate.project_id, pick)


async def test_preview_refuses_a_row_with_no_http_exchange(estate, now):
    (finding,) = await _findings(estate, now, request=None)
    finding.protocol = Protocol.DNS.value
    finding.matched_at = HOST
    await estate.session.flush()
    service, row = await _connector(estate)
    with pytest.raises(HandoffError, match="carries no HTTP request"):
        await service.preview(
            row.id, estate.project_id, HandoffRequest(finding_ids=[finding.id])
        )


# ---------- sending an edited request ----------


async def test_an_edited_request_goes_to_the_row_own_target(estate, now):
    (finding,) = await _findings(
        estate, now, request=f"GET /api HTTP/1.1\r\nHost: {HOST}\r\n\r\n"
    )
    service, row = await _connector(estate)

    result = await service.handoff(
        row.id,
        estate.project_id,
        HandoffRequest(
            kind=ActionKind.ORGANIZER.value,
            finding_ids=[finding.id],
            request="POST /api HTTP/1.1\nHost: other.example\nX-Test: 1\n\nid=7",
        ),
    )
    assert (result.queued, result.skipped) == (1, 0)

    (sent,) = await service.take_actions(row)
    assert sent.url == f"https://{HOST}/", "the row's URL stays the target"
    assert sent.method == "POST"
    assert sent.request == (
        "POST /api HTTP/1.1\r\nHost: other.example\r\nX-Test: 1\r\n"
        "Content-Length: 4\r\n\r\nid=7"
    )
    assert sent.notes.startswith("reNgine · High · cve-0"), "the note stays as built"


async def test_an_edited_request_needs_one_row_and_a_valid_head(estate, now):
    first, second = await _findings(estate, now, request=None, count=2)
    service, row = await _connector(estate)
    edit = f"GET / HTTP/1.1\nHost: {HOST}\n\n"

    with pytest.raises(HandoffError, match="Select exactly one row"):
        await service.handoff(
            row.id,
            estate.project_id,
            HandoffRequest(finding_ids=[first.id, second.id], request=edit),
        )
    with pytest.raises(HandoffError, match="no Host header"):
        await service.handoff(
            row.id,
            estate.project_id,
            HandoffRequest(finding_ids=[first.id], request="GET / HTTP/1.1\n\n"),
        )
    assert await service.take_actions(row) == [], "a refused edit queues nothing"


async def test_masked_values_in_an_edit_are_restored_and_typed_ones_kept(estate, now):
    (finding,) = await _findings(
        estate,
        now,
        request=f"GET / HTTP/1.1\r\nHost: {HOST}\r\nAuthorization: Bearer {MASK}\r\n\r\n",
        config={"headers": seal_headers({"Authorization": "Bearer real-token"})},
    )
    service, row = await _connector(estate)
    row.restore_credentials = True

    await service.handoff(
        row.id,
        estate.project_id,
        HandoffRequest(
            finding_ids=[finding.id],
            request=f"GET / HTTP/1.1\nHost: {HOST}\nAuthorization: Bearer {MASK}\nX-Test: 1\n\n",
        ),
    )
    stored = await estate.session.scalar(
        select(ConnectorAction.request).where(ConnectorAction.connector_id == row.id)
    )
    (restored,) = await service.take_actions(row)
    assert "Authorization: Bearer real-token\r\nX-Test: 1\r\n" in restored.request
    assert "real-token" not in stored, "the queue row keeps the masked text"

    await service.handoff(
        row.id,
        estate.project_id,
        HandoffRequest(
            finding_ids=[finding.id],
            request=f"GET / HTTP/1.1\nHost: {HOST}\nAuthorization: Bearer typed\n\n",
        ),
    )
    (typed,) = await service.take_actions(row)
    assert "Authorization: Bearer typed\r\n" in typed.request
    assert "real-token" not in typed.request


def test_client_file_is_the_highest_release(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "CLIENT_DIR", tmp_path)
    assert BurpConnector().client_file == ""
    for version in ("0.9.0", "0.10.0", "0.2.1"):
        (tmp_path / f"rengine-connector-{version}.jar").write_bytes(b"")
    (tmp_path / "other-1.0.jar").write_bytes(b"")
    assert BurpConnector().client_file == "rengine-connector-0.10.0.jar"
    assert base.release_key(
        "rengine-connector-1.2.3.jar", "rengine-connector-*.jar"
    ) == (
        (1, 2, 3),
        "rengine-connector-1.2.3.jar",
    )
