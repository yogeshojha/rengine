from __future__ import annotations

import pytest

from shared.definitions.name_ownership import CLAIM_TEMPLATES, NameClaim
from shared.definitions.vulnerabilities import Scanner, Severity
from shared.services.name_ownership import Asset, judge
from stages.name_ownership.finding import claim_finding
from stages.name_ownership.stage import NameOwnershipStage

pytestmark = pytest.mark.pipeline

ROOT = "gov.example"
BODY = '<a href="https://www.tenant.shop/a">a</a>' * 4 + "x" * 600


def _asset(host: str, **kw) -> Asset:
    base = {
        "host": host,
        "url": f"https://{host}",
        "ip": "198.51.100.7",
        "port": 443,
        "scheme": "https",
        "status_code": 200,
        "title": "Tenant Shop | Home",
        "final_url": "https://www.tenant.shop/",
        "location": None,
        "tls_subject_cn": "tenant.shop",
        "tls_sans": ["tenant.shop", "www.tenant.shop"],
        "is_cdn": False,
        "content_hash": "abc",
        "content_length": 900,
        "asn_org": "Shared Hosting Ltd",
        "body": BODY,
    }
    base.update(kw)
    return Asset(**base)


def test_an_owned_name_serving_another_site_is_claimed():
    found = judge(
        [_asset("dado.gov.example"), _asset("www.dado.gov.example")], ROOT, set()
    )

    assert [c.kind for c in found] == [NameClaim.FOREIGN_SITE.value] * 2
    assert found[0].domain == "tenant.shop"
    assert found[0].siblings == 1


def test_a_page_that_mentions_the_target_is_not_claimed():
    body = BODY + '<a href="https://portal.gov.example/">portal</a>'
    assert judge([_asset("dado.gov.example", body=body)], ROOT, set()) == []


def test_the_owners_other_domain_is_not_claimed():
    asset = _asset(
        "tourism.gov.example",
        final_url="https://tourismboard.org/",
        tls_subject_cn="tourismboard.org",
        tls_sans=["tourismboard.org"],
        body='<a href="https://tourismboard.org/x">x</a>' * 4,
    )
    assert judge([asset], ROOT, set()) == []


def test_a_brand_domain_is_not_claimed():
    asset = _asset(
        "shop.acme.com",
        final_url="https://acme-store.ru/",
        tls_subject_cn="acme-store.ru",
        tls_sans=[],
        body='<a href="https://acme-store.ru/x">x</a>' * 4,
    )
    assert judge([asset], "acme.com", set()) == []


def test_another_target_of_the_project_is_not_claimed():
    assert judge([_asset("dado.gov.example")], ROOT, {"tenant.shop"}) == []


def test_a_sign_in_redirect_is_not_claimed():
    asset = _asset(
        "git.gov.example",
        final_url="https://github.com/login",
        tls_subject_cn="github.com",
        tls_sans=["github.com"],
        body='<a href="https://github.com/x">x</a>' * 4,
    )
    assert judge([asset], ROOT, set()) == []


def test_a_cdn_fronted_name_is_not_claimed():
    assert judge([_asset("dado.gov.example", is_cdn=True)], ROOT, set()) == []


def test_a_default_page_on_a_foreign_certificate_is_unhosted():
    default = _asset(
        "198.51.100.7",
        title="403 - FORBIDDEN",
        status_code=403,
        final_url=None,
        body="forbidden " * 80,
        tls_subject_cn="host123.hosting.example",
        tls_sans=[],
    )
    named = _asset(
        "office.gov.example",
        title="403 - FORBIDDEN",
        status_code=403,
        final_url=None,
        body="forbidden " * 80,
        tls_subject_cn="host123.hosting.example",
        tls_sans=[],
    )
    found = judge([default, named], ROOT, set())

    assert [(c.host, c.kind, c.domain) for c in found] == [
        ("office.gov.example", NameClaim.UNHOSTED.value, "hosting.example")
    ]


def test_a_certificate_alone_is_not_enough():
    asset = _asset("office.gov.example", final_url=None, body="plain page " * 80)
    assert judge([asset], ROOT, set()) == []


def test_a_same_tld_redirect_to_an_error_page_is_not_claimed():
    asset = _asset(
        "eservices.gov.example",
        title="ERROR: The request could not be satisfied",
        status_code=403,
        final_url="https://platform.example/",
        tls_subject_cn="platform.example",
        tls_sans=[],
        body="error " * 100,
    )
    assert judge([asset], ROOT, set()) == []


def test_the_finding_names_the_domain_and_is_stable():
    claim = judge([_asset("dado.gov.example")], ROOT, set())[0]
    a = claim_finding(claim, ROOT)
    b = claim_finding(claim, ROOT)

    assert a.fingerprint == b.fingerprint
    assert a.scanner == Scanner.RENGINE.value
    assert a.template_id == CLAIM_TEMPLATES[NameClaim.FOREIGN_SITE.value]
    assert a.severity == Severity.HIGH.value
    assert a.matcher_name == "tenant.shop"
    assert "References to gov.example: none" in a.description


def test_the_stage_sends_nothing_and_produces_findings():
    assert NameOwnershipStage.touches_target is False
    assert "vulnerabilities" in NameOwnershipStage.produces
