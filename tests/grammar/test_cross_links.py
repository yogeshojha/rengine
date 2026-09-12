from __future__ import annotations

import uuid

import pytest

from app.services.cross_links import _TOKEN_OP, Carrier
from shared.definitions.asset_query import HOST_QUERY
from shared.definitions.correlation import (
    CORRELATION_KIND_LABELS,
    CROSS_LINK_ORDER,
    CROSS_PAGE_KINDS,
    CorrelationKind,
)
from shared.services.asset_query.groups import _DIMENSIONS
from shared.utils.infra import generic_page
from shared.utils.net import cert_covers

pytestmark = pytest.mark.grammar

TARGET = uuid.uuid4()

# measured across four unrelated estates on 2026-09-12: every cross-target title was one of these
MEASURED_GENERIC = [
    ("404 Not Found", 404),
    ("403 Forbidden", 403),
    ("404 - Page not found", 200),
    ("Just a moment...", 403),
    ("", 200),
]

MEASURED_REAL = [
    ("Shopify Academy", 200),
    ("Uber Freight", 200),
    ("Grafana", 200),
    ("Error 404 on our Jenkins", 200),
]


@pytest.mark.parametrize("kind", list(CROSS_LINK_ORDER))
def test_every_kind_can_be_drawn_and_searched(kind: str):
    assert kind in CORRELATION_KIND_LABELS, "the chip has no label for it"
    assert kind in _DIMENSIONS, "a link could not carry a drill-down token"
    assert HOST_QUERY.by_name.get(kind) is not None, "the token would not compile"
    assert _DIMENSIONS[kind][2] == _TOKEN_OP.get(kind, "="), "the token uses another op"


def test_jarm_is_not_a_cross_link():
    assert CorrelationKind.JARM.value not in CROSS_LINK_ORDER


@pytest.mark.parametrize(("title", "status"), MEASURED_GENERIC)
def test_a_server_page_is_refused(title: str, status: int):
    assert generic_page(title, [status]) is not None


@pytest.mark.parametrize(("title", "status"), MEASURED_REAL)
def test_an_application_page_is_kept(title: str, status: int):
    assert generic_page(title, [status]) is None


@pytest.mark.parametrize("kind", sorted(CROSS_PAGE_KINDS))
def test_a_server_page_vouches_for_no_identity(kind: str):
    carrier = Carrier("a.example.com", TARGET, None, 404, "404 Not Found")
    assert carrier.vouches(kind) is False


@pytest.mark.parametrize("kind", list(CROSS_LINK_ORDER))
def test_a_shared_platform_tenant_vouches_for_nothing(kind: str):
    carrier = Carrier(
        "docs.example.com",
        TARGET,
        "ghs.googlehosted.com",
        200,
        "Sign in - Google Accounts",
        "*.example.com",
        ("*.example.com",),
    )
    assert carrier.vouches(kind) is False


def test_a_certificate_vouches_only_when_it_names_the_host():
    vendor = Carrier(
        "admin.collabs.example.com",
        TARGET,
        None,
        200,
        "Example - Sign In",
        "*.okta.com",
        ("*.okta.com", "okta.com"),
    )
    own = Carrier(
        "www.example.com",
        TARGET,
        None,
        200,
        "Example",
        "*.example.com",
        ("*.example.com", "www.brand2.com"),
    )
    kind = CorrelationKind.CERT.value
    assert vendor.vouches(kind) is False
    assert own.vouches(kind) is True


def test_a_certificate_names_a_second_brand_through_its_sans():
    assert cert_covers("www.brand2.com", "*.acme.com", ["*.acme.com", "www.brand2.com"])
    assert not cert_covers("a.b.acme.com", "*.acme.com", ["*.acme.com"])


def test_an_application_page_vouches():
    carrier = Carrier("app.example.com", TARGET, None, 200, "Acme Internal Console")
    for kind in CROSS_PAGE_KINDS:
        assert carrier.vouches(kind) is True
