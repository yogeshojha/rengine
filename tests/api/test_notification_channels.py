"""A channel's stored URL is masked on the way out and checked on the way in."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.notification_channel import (
    _mask_config,
    _mask_url,
    _validate_config,
)
from shared.enums.notification_channel import NotificationProvider
from shared.services.notifier import build_apprise_url
from shared.services.scan_resolve import MASK, mask_tail
from shared.utils.net import validate_public_https_url

pytestmark = pytest.mark.api

CUSTOM = NotificationProvider.CUSTOM.value
EMAIL = NotificationProvider.EMAIL.value
SMTP = {"username": "ops", "password": "x", "to_email": "soc@example.com"}


@pytest.mark.parametrize(
    "url",
    [
        "https://hooks.example.com/services/abc",
        "https://hooks.example.com:8443/services/abc",
        "https://hooks.example.com:99999/services/abc",
        "https://hooks.example.com:8o80/services/abc",
        "https://[2001:db8::1]:8443/hook",
    ],
)
def test_masking_a_url_never_raises_on_the_port(url):
    masked = _mask_url(url)
    assert MASK in masked
    assert "abc" not in masked


@pytest.mark.parametrize(
    ("value", "masked"),
    [("abcd", MASK), ("abcdefgh", MASK), ("abcdefghij", f"{MASK}ghij")],
)
def test_a_secret_shows_a_tail_only_when_longer_than_eight(value, masked):
    assert mask_tail(value) == masked


def test_an_smtp_password_shows_no_tail():
    masked = _mask_config(EMAIL, {"password": "correct-horse-battery"})
    assert masked["password"] == MASK


def test_a_port_that_is_not_a_number_is_refused_before_it_is_stored():
    with pytest.raises(ValueError, match="not a port number"):
        validate_public_https_url(
            "https://hooks.example.com:99999/x", label="Webhook URL"
        )


@pytest.mark.parametrize(
    "url",
    [
        "gotify://redis:6379/abcdefghijklmnop",
        "ntfy://169.254.169.254/topic",
        "apprise://api:8000/token",
        "json://example.com/hook",
        "slack://T000/B000/XXXX, gotify://redis:6379/abcdefghijklmnop",
        "not a url",
    ],
)
def test_a_custom_channel_refuses_a_service_at_a_chosen_host(url):
    with pytest.raises(HTTPException):
        _validate_config(CUSTOM, {"apprise_url": url})


def test_a_custom_channel_takes_a_service_at_a_fixed_host():
    _validate_config(CUSTOM, {"apprise_url": "slack://T000/B000/XXXX"})


def test_a_stored_custom_url_off_the_list_is_not_sent():
    assert build_apprise_url(CUSTOM, {"apprise_url": "gotify://redis:6379/x"}) is None
    assert build_apprise_url(CUSTOM, {"apprise_url": "slack://T000/B000/X"})


@pytest.mark.parametrize(
    "host",
    [
        "127.0.0.1",
        "localhost",
        "169.254.169.254",
        "0.0.0.0",  # noqa: S104
        "relay gotify://redis:6379/abcdefghijklmnop",
        "relay/path",
    ],
)
def test_an_smtp_host_on_this_machine_or_the_metadata_service_is_refused(host):
    with pytest.raises(HTTPException):
        _validate_config(EMAIL, {**SMTP, "smtp_host": host})


def test_an_smtp_port_that_is_not_a_number_is_refused():
    with pytest.raises(HTTPException):
        _validate_config(
            EMAIL, {**SMTP, "smtp_host": "10.0.0.25", "smtp_port": "25 x://y"}
        )


def test_an_smtp_relay_on_the_private_network_is_kept():
    _validate_config(EMAIL, {**SMTP, "smtp_host": "10.0.0.25", "smtp_port": 25})
