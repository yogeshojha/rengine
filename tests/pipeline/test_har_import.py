"""The HAR path, which is how any proxy without a native client reaches reNgine."""

from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
from pathlib import Path

import pytest

from shared.models.connector import IngestItem, IngestRequest

pytestmark = pytest.mark.pipeline

_SOURCE = Path(__file__).resolve().parents[2] / "clients" / "har" / "rengine_har.py"
_spec = importlib.util.spec_from_file_location("rengine_har", _SOURCE)
har = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(har)


def _entry(**over) -> dict:
    entry = {
        "startedDateTime": "2026-09-11T03:40:00.000Z",
        "request": {
            "method": "GET",
            "url": "https://a.example.com/admin",
            "headers": [],
        },
        "response": {"status": 200, "content": {"mimeType": "text/html", "size": 12}},
    }
    for key, value in over.items():
        if key in ("request", "response"):
            entry[key] = {**entry[key], **value}
        else:
            entry[key] = value
    return entry


# ── what is read out of an entry ──


def test_an_entry_becomes_a_shape():
    row = har.item(_entry())
    assert row["url"] == "https://a.example.com/admin"
    assert row["method"] == "GET"
    assert row["status_code"] == 200
    assert row["content_length"] == 12
    assert row["source_tool"] == "proxy"


def test_the_method_is_upper_cased():
    assert har.item(_entry(request={"method": "post"}))["method"] == "POST"


@pytest.mark.parametrize(
    "url",
    [
        "chrome-extension://abc/x.js",
        "ws://a.example.com/socket",
        "data:text/html,hi",
        "",
        "not a url",
    ],
)
def test_anything_that_is_not_an_http_request_is_dropped(url: str):
    assert har.item(_entry(request={"url": url})) is None


def test_a_page_title_is_read_from_html():
    row = har.item(
        _entry(
            response={
                "status": 200,
                "content": {
                    "mimeType": "text/html",
                    "size": 40,
                    "text": "<title>Prijava</title>",
                },
            }
        )
    )
    assert row["title"] == "Prijava"


def test_a_title_is_not_invented_from_a_non_html_body():
    row = har.item(
        _entry(
            response={
                "status": 200,
                "content": {
                    "mimeType": "application/json",
                    "size": 40,
                    "text": "<title>x</title>",
                },
            }
        )
    )
    assert row["title"] is None


def test_body_parameter_names_travel_and_their_values_do_not():
    row = har.item(
        _entry(
            request={
                "method": "POST",
                "postData": {
                    "params": [
                        {"name": "username", "value": "admin"},
                        {"name": "password", "value": "hunter2"},
                    ]
                },
            }
        )
    )
    assert row["body_params"] == ["username", "password"]
    assert "hunter2" not in str(row)


def test_a_session_is_noticed_without_being_sent():
    """The whole point: reNgine learns the request was authenticated, not what with."""
    row = har.item(
        _entry(request={"headers": [{"name": "Cookie", "value": "sid=secret-value"}]})
    )
    assert row["authenticated"] is True
    assert "secret-value" not in str(row)


def test_no_credential_header_means_not_authenticated():
    row = har.item(_entry(request={"headers": [{"name": "Accept", "value": "*/*"}]}))
    assert row["authenticated"] is False


def test_no_header_at_all_is_never_sent():
    """The Burp client sends no headers either; the contract is the same one."""
    row = har.item(
        _entry(request={"headers": [{"name": "Authorization", "value": "Bearer t"}]})
    )
    assert "Bearer" not in str(row)
    assert "request_sample" not in row


def test_a_missing_status_is_none_not_zero():
    assert har.item(_entry(response={"status": 0}))["status_code"] is None


def test_a_body_size_falls_back_to_the_transfer_size():
    row = har.item(
        _entry(
            response={
                "status": 200,
                "content": {"mimeType": "text/html"},
                "bodySize": 99,
            }
        )
    )
    assert row["content_length"] == 99


# ── the file, and what goes on the wire ──


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    path = tmp_path / "h.har"
    path.write_text(json.dumps({"log": {"version": "1.2", "entries": entries}}))
    return path


def test_a_har_file_is_read(tmp_path: Path):
    path = _write(
        tmp_path, [_entry(), _entry(request={"url": "https://a.example.com/x"})]
    )
    assert len(har.read(path)) == 2


def test_a_har_with_no_entries_is_not_an_error(tmp_path: Path):
    assert har.read(_write(tmp_path, [])) == []


def test_the_same_request_twice_is_sent_once():
    rows = [har.item(_entry()), har.item(_entry())]
    assert len(har.dedupe(rows)) == 1


def test_the_same_url_by_two_methods_is_two_requests():
    rows = [har.item(_entry()), har.item(_entry(request={"method": "POST"}))]
    assert len(har.dedupe(rows)) == 2


def test_an_out_of_scope_host_is_still_sent():
    """reNgine decides scope; discarding here is unrecoverable."""
    row = har.item(_entry(request={"url": "https://telemetry.vendor.io/collect"}))
    assert row is not None


def test_a_batch_never_exceeds_what_the_endpoint_accepts():
    cap = IngestRequest.model_fields["items"].metadata
    limit = next(m.max_length for m in cap if hasattr(m, "max_length"))
    assert limit >= har.BATCH


def test_the_url_cap_matches_the_endpoint():
    cap = IngestItem.model_fields["url"].metadata
    limit = next(m.max_length for m in cap if hasattr(m, "max_length"))
    assert limit >= har.MAX_URL


def test_every_field_it_sends_is_one_the_endpoint_accepts():
    """IngestItem forbids extras, so one stray key rejects the whole batch."""
    assert set(har.item(_entry())) <= set(IngestItem.model_fields)


def _raises(code: int, monkeypatch) -> None:
    def _open(*_a, **_kw):
        url, reason = "http://x", "no"
        raise urllib.error.HTTPError(url, code, reason, {}, io.BytesIO(b"denied"))

    monkeypatch.setattr(har.urllib.request, "urlopen", _open)


def test_a_rejected_token_stops_rather_than_retrying(monkeypatch):
    """The endpoint sits behind a per-IP failure limiter; retrying locks you out."""
    _raises(401, monkeypatch)
    with pytest.raises(har.TokenRefusedError):
        har.post("http://x", "t", [{"url": "https://a/b"}], "har")


def test_another_failure_is_not_read_as_a_rejected_token(monkeypatch):
    """A 500 is the server's problem; calling it a bad token sends the user rotating one."""
    _raises(500, monkeypatch)
    with pytest.raises(SystemExit):
        har.post("http://x", "t", [{"url": "https://a/b"}], "har")


def test_an_unreachable_endpoint_says_so(monkeypatch):
    def _open(*_a, **_kw):
        refused = "connection refused"
        raise urllib.error.URLError(refused)

    monkeypatch.setattr(har.urllib.request, "urlopen", _open)
    with pytest.raises(SystemExit, match="could not reach"):
        har.post("http://x", "t", [{"url": "https://a/b"}], "har")


def test_the_token_is_sent_as_a_bearer(monkeypatch):
    sent: dict = {}

    class _Response:
        def read(self):
            return b'{"accepted": 1}'

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def _open(request, **_kw):
        sent["headers"] = dict(request.headers)
        sent["body"] = json.loads(request.data)
        return _Response()

    monkeypatch.setattr(har.urllib.request, "urlopen", _open)
    har.post("http://x", "tok", [{"url": "https://a/b"}], "caido")

    assert sent["headers"]["Authorization"] == "Bearer tok"
    assert sent["body"]["client"] == "caido"
