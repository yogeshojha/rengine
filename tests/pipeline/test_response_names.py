from __future__ import annotations

import pytest

from shared.services.response_names import harvest

pytestmark = pytest.mark.pipeline

ROOT = "gov.example"


def _row(subject=None, sans=None, header=None, location=None, final=None, body=None):
    return (subject, sans, header, location, final, body)


def test_certificate_names_under_the_root_are_read():
    found = harvest(
        [_row("portal.gov.example", ["*.mail.gov.example", "vendor.com"])], ROOT
    )

    assert found == {
        "portal.gov.example": {"tls_cert"},
        "mail.gov.example": {"tls_cert"},
    }


def test_a_policy_header_names_hosts():
    header = (
        "Content-Security-Policy: connect-src 'self' https://api.gov.example "
        "http://10.1.2.3:81\r\n"
    )
    assert harvest([_row(header=header)], ROOT) == {
        "api.gov.example": {"response_header"}
    }


def test_escaped_links_in_a_page_are_read():
    body = (
        '{"u":"https:\\/\\/data.gov.example\\/x"} '
        '<a href="/go?to=https%3A%2F%2Frsud.city.gov.example%2Fa">x</a> '
        "mail info@office.gov.example"
    )
    assert set(harvest([_row(body=body)], ROOT)) == {
        "data.gov.example",
        "rsud.city.gov.example",
        "office.gov.example",
    }


def test_a_lookalike_domain_is_not_read():
    body = "https://login.gov.example.evil.com/ https://gov.examples.org/"
    assert harvest([_row(body=body)], ROOT) == {}


def test_a_redirect_target_is_read():
    found = harvest([_row(location="https://new.gov.example/start")], ROOT)
    assert found == {"new.gov.example": {"redirect"}}


def test_one_name_keeps_every_place_it_was_read():
    found = harvest(
        [
            _row(sans=["app.gov.example"]),
            _row(body='<a href="https://app.gov.example/">app</a>'),
        ],
        ROOT,
    )
    assert found == {"app.gov.example": {"tls_cert", "page_link"}}
