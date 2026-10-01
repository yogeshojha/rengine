"""What a channel receives: plain text, the link last, nothing parsed."""

from __future__ import annotations

from typing import ClassVar

import pytest

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
