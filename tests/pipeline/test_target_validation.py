from __future__ import annotations

import pytest

from shared.enums.target import TargetType
from shared.utils.validation import (
    MAX_ASN,
    normalize_target_value,
    unrecognised_target,
    validate_target,
)

pytestmark = pytest.mark.pipeline


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("EXAMPLE.COM", "example.com"),
        ("Example.Com", "example.com"),
        ("*.Example.COM", "example.com"),
        ("  Example.com.  ", "example.com"),
        ("AS13335", "as13335"),
    ],
)
def test_a_host_folds_to_one_value(raw, expected):
    assert normalize_target_value(raw) == expected


def test_a_url_keeps_the_case_of_its_path():
    value = normalize_target_value("HTTPS://Example.COM/Artists.php?Artist=One")

    assert value == "https://example.com/Artists.php?Artist=One"


def test_a_url_keeps_its_userinfo():
    assert normalize_target_value("https://User:PaSS@Example.com/") == (
        "https://User:PaSS@example.com/"
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("example.com", TargetType.DOMAIN),
        ("AS13335", TargetType.ASN),
        (f"AS{MAX_ASN}", TargetType.ASN),
        ("1.1.1.1", TargetType.IP),
        ("2606:4700:4700::1111", TargetType.IP),
        ("192.168.1.0/24", TargetType.IP_RANGE),
        ("10.0.0.0/8", TargetType.IP_RANGE),
        ("https://example.com/a", TargetType.URL),
    ],
)
def test_a_scannable_target_is_recognised(value, expected):
    assert validate_target(value) is expected


@pytest.mark.parametrize(
    "value",
    [
        "0.0.0.0/0",
        "::/0",
        "127.0.0.1",
        "127.0.0.0/8",
        "169.254.169.254",
        "::1",
        "224.0.0.1",
        "AS0",
        f"AS{MAX_ASN + 1}",
        "AS99999999999999999999",
    ],
)
def test_an_out_of_bounds_target_is_refused(value):
    assert validate_target(value) is None


def test_a_private_range_stays_available_for_corporate_estates():
    assert validate_target("10.0.0.0/8") is TargetType.IP_RANGE


def test_the_default_route_says_what_is_wrong():
    assert unrecognised_target("0.0.0.0/0") == (
        "0.0.0.0/0 covers every address. Enter the range you own."
    )


def test_an_out_of_range_asn_says_the_range():
    assert unrecognised_target("AS99999999999999999999") == (
        f"AS99999999999999999999 is out of range. An AS number runs from 1 to {MAX_ASN}."
    )


def test_reserved_space_says_what_is_out_of_scope():
    assert "Loopback, link-local, multicast" in unrecognised_target("127.0.0.1")


def test_plain_nonsense_still_gets_the_format_hint():
    assert "Unrecognised target" in unrecognised_target("not a target at all")
