"""What a channel receives: plain text, the link last, nothing parsed."""

from __future__ import annotations

import socket
from typing import ClassVar

import httpcore
import httpx
import pytest

from shared import http
from shared.services import notifier
from shared.services.notifier import Outbound, build_apprise_url, send_one

pytestmark = pytest.mark.api

META = {"url": "/scans/abc?tab=vulnerabilities", "scan_id": "abc"}


def _message(
    title="14 critical findings on gov.np", body="141 new findings\n3 known exploited"
):
    return Outbound.build("vulnerability", "error", title, body, META)


class _Response:
    is_success = True
    status_code = 200


class _Client:
    posts: ClassVar[list[tuple[str, dict | None, dict | None, list[str]]]] = []

    def __init__(self, **_kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def post(self, url, json=None, data=None, files=None, **_kwargs):
        _Client.posts.append((url, json, data, list((files or {}).keys())))
        return _Response()


@pytest.fixture
def posts(monkeypatch):
    _Client.posts = []
    monkeypatch.setattr(notifier, "get_sync_client", lambda **_k: _Client())
    monkeypatch.setattr(notifier, "get_public_client", lambda **_k: _Client())
    monkeypatch.setattr(notifier, "validate_public_https_url", lambda *_a, **_k: None)
    return _Client.posts


def test_the_text_is_title_facts_and_the_absolute_link():
    message = _message()
    assert message.url.endswith("/scans/abc?tab=vulnerabilities")
    assert message.url.startswith("http")
    assert message.text().split("\n") == [
        "14 critical findings on gov.np",
        "141 new findings",
        "3 known exploited",
        message.url,
    ]


def test_slack_and_discord_carry_no_apprise_branding():
    slack = build_apprise_url(
        "slack",
        {"webhook_url": "https://hooks.slack.com/services/T0ABCDEFG/B0ABCDEFG/abcdef"},
    )
    assert slack is not None
    assert "footer=no" in slack
    assert "image=no" in slack
    discord = build_apprise_url(
        "discord", {"webhook_url": "https://discord.com/api/webhooks/123/abc"}
    )
    assert discord is not None
    assert "avatar=no" in discord


def test_discord_bolds_the_title_in_plain_content():
    title, body = notifier._apprise_text("discord", _message())
    assert title == ""
    assert body.startswith("**14 critical findings on gov.np**\n141 new findings")


def test_telegram_is_posted_verbatim_with_a_bold_entity(posts):
    message = Outbound.build(
        "tripwire",
        "info",
        "Tripwire · Üñí",
        "admin.x.com · 200 · <script>alert(1)</script> & Co",
        {"url": "/tripwires?run=r"},
    )
    ok, reason = send_one("telegram", {"bot_token": "1:a", "chat_id": "-1"}, message)
    assert (ok, reason) == (True, "")
    url, payload, _data, _files = posts[0]
    assert url.endswith("/sendMessage")
    assert "parse_mode" not in payload
    assert (
        payload["text"].split("\n")[1]
        == "admin.x.com · 200 · <script>alert(1)</script> & Co"
    )
    assert payload["entities"] == [{"type": "bold", "offset": 0, "length": 14}]


def test_telegram_sends_the_attachment_after_the_text(posts, tmp_path):
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"png")
    message = Outbound.build(
        "watch", "info", "New in-scope asset", "a.b.c", {}, str(shot)
    )
    assert send_one("telegram", {"bot_token": "1:a", "chat_id": "-1"}, message) == (
        True,
        "",
    )
    assert [p[0].rsplit("/", 1)[1] for p in posts] == ["sendMessage", "sendPhoto"]
    assert posts[1][3] == ["photo"]


def test_the_webhook_payload_names_the_event_and_where_it_lands(posts):
    assert send_one("webhook", {"webhook_url": "https://x/h"}, _message()) == (True, "")
    payload = posts[0][1]
    assert payload["type"] == "vulnerability"
    assert payload["severity"] == "error"
    assert payload["scan_id"] == "abc"
    assert payload["url"].endswith("/scans/abc?tab=vulnerabilities")
    assert set(payload) == {
        "source",
        "type",
        "severity",
        "title",
        "message",
        "url",
        "scan_id",
        "target_id",
        "sent_at",
    }


def test_teams_gets_an_adaptive_card_with_an_open_action(posts):
    assert send_one("teams", {"webhook_url": "https://x/h"}, _message()) == (True, "")
    card = posts[0][1]["attachments"][0]["content"]
    assert card["type"] == "AdaptiveCard"
    assert [b["text"] for b in card["body"]] == [
        "14 critical findings on gov.np",
        "141 new findings",
        "3 known exploited",
    ]
    assert card["body"][0]["color"] == "Attention"
    assert card["actions"][0]["url"].endswith("/scans/abc?tab=vulnerabilities")


def test_a_failed_post_reports_the_status_and_nothing_else(posts, monkeypatch):
    monkeypatch.setattr(_Response, "is_success", False)
    monkeypatch.setattr(_Response, "status_code", 404)
    assert send_one("webhook", {"webhook_url": "https://x/h"}, _message()) == (
        False,
        "HTTP 404",
    )
    assert send_one("telegram", {"chat_id": "-1"}, _message()) == (
        False,
        notifier.INVALID_CONFIG,
    )


def test_a_stored_webhook_on_a_private_address_is_not_posted(monkeypatch):
    _Client.posts = []
    monkeypatch.setattr(notifier, "get_public_client", lambda **_k: _Client())
    ok, reason = send_one("webhook", {"webhook_url": "https://127.0.0.1/h"}, _message())
    assert ok is False
    assert "disallowed address" in reason
    assert _Client.posts == []


def test_a_name_that_resolves_private_at_connect_time_is_refused(monkeypatch):
    monkeypatch.setattr(
        http.socket,
        "getaddrinfo",
        lambda *_a, **_k: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 443))
        ],
    )
    with (
        httpx.Client(transport=http.PublicTransport()) as client,
        pytest.raises(httpx.ConnectError, match="not public"),
    ):
        client.post("https://hooks.example.com/h", json={})


async def test_the_async_transport_refuses_a_private_answer(monkeypatch):
    monkeypatch.setattr(
        http.socket,
        "getaddrinfo",
        lambda *_a, **_k: [
            (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", 443, 0, 0))
        ],
    )
    async with httpx.AsyncClient(transport=http.AsyncPublicTransport()) as client:
        with pytest.raises(httpx.ConnectError, match="not public"):
            await client.get("https://oast.example.com/poll")


def _two_public_answers(monkeypatch):
    monkeypatch.setattr(
        http.socket,
        "getaddrinfo",
        lambda *_a, **_k: [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                6,
                "",
                ("2606:4700::1111", 443, 0, 0),
            ),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 443)),
        ],
    )


def test_the_next_public_address_is_dialled_when_one_does_not_connect(monkeypatch):
    _two_public_answers(monkeypatch)
    dialled: list[str] = []

    def connect(_self, host, *_a, **_k):
        dialled.append(host)
        if ":" in host:
            raise httpcore.ConnectError(host)
        return "stream"

    monkeypatch.setattr(httpcore.SyncBackend, "connect_tcp", connect)
    assert http._PublicBackend().connect_tcp("hooks.example.com", 443) == "stream"
    assert dialled == ["2606:4700::1111", "1.1.1.1"]


async def test_the_async_backend_dials_the_next_public_address(monkeypatch):
    _two_public_answers(monkeypatch)

    async def connect(_self, host, *_a, **_k):
        if ":" in host:
            raise httpcore.ConnectTimeout(host)
        return "stream"

    monkeypatch.setattr(httpcore.AnyIOBackend, "connect_tcp", connect)
    backend = http._AsyncPublicBackend()
    assert await backend.connect_tcp("oast.example.com", 443) == "stream"


def test_a_user_url_goes_through_the_egress_proxy_when_one_is_set(monkeypatch):
    url = httpx.URL("https://hooks.example.com/h")
    monkeypatch.setattr(http, "egress_proxy", lambda: "http://10.0.0.5:3128")
    with http.get_public_client() as client:
        transport = client._transport_for_url(url)
        assert not isinstance(transport, http.PublicTransport)
        assert isinstance(transport._pool, httpcore.HTTPProxy)
        assert client.follow_redirects is False
    monkeypatch.setattr(http, "egress_proxy", lambda: None)
    with http.get_public_client() as client:
        assert isinstance(client._transport_for_url(url), http.PublicTransport)
