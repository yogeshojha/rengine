from __future__ import annotations

import pytest

from shared.services.origin_exposure import (
    ORIGIN_EXPOSED,
    OriginExposureService,
    _Asset,
)
from stages.origin_probe.confirm import Page, same_site

pytestmark = pytest.mark.pipeline


def _asset(host, ip, *, cdn=False, prints=None, port=443, status=200) -> _Asset:
    return _Asset(
        host=host,
        url=f"https://{host}",
        ip=ip,
        port=port,
        status_code=status,
        title="Acme Portal",
        webserver="nginx",
        is_cdn=cdn,
        cdn_name="Cloudflare" if cdn else None,
        asn_org=None,
        screenshot_path=None,
        content_length=4096,
        prints=prints or {},
    )


def _origins(origin: _Asset, fronted: _Asset, resolved=None):
    service = OriginExposureService(session=None)  # type: ignore[arg-type]
    return service._origins([origin, fronted], [fronted], {}, resolved or {})


def test_a_shared_body_on_an_address_the_cdn_does_not_front_is_a_candidate():
    origin = _asset("2.2.2.2", "2.2.2.2", prints={"content_hash": "abc"})
    fronted = _asset(
        "www.example.com", "1.1.1.1", cdn=True, prints={"content_hash": "abc"}
    )
    found = _origins(origin, fronted)
    assert [f.kind for f in found] == [ORIGIN_EXPOSED]


def test_a_name_that_already_resolves_to_the_address_is_not_a_bypass():
    origin = _asset("2.2.2.2", "2.2.2.2", prints={"content_hash": "abc"})
    fronted = _asset(
        "www.example.com", "1.1.1.1", cdn=True, prints={"content_hash": "abc"}
    )
    resolved = {"www.example.com": {"1.1.1.1", "2.2.2.2"}}
    assert _origins(origin, fronted, resolved) == []


def test_a_certificate_alone_does_not_mint_a_candidate():
    origin = _asset("2.2.2.2", "2.2.2.2", prints={"tls_fingerprint": "cert"})
    fronted = _asset(
        "www.example.com", "1.1.1.1", cdn=True, prints={"tls_fingerprint": "cert"}
    )
    assert _origins(origin, fronted) == []


def test_a_certificate_corroborates_a_body_it_shares():
    prints = {"tls_fingerprint": "cert", "content_hash": "abc"}
    origin = _asset("2.2.2.2", "2.2.2.2", prints=prints)
    fronted = _asset("www.example.com", "1.1.1.1", cdn=True, prints=prints)
    found = _origins(origin, fronted)
    assert len(found) == 1
    assert found[0].confidence == "high"
    assert {item.kind for item in found[0].evidence} == set(prints)


def _page(digest="d", title="Acme Portal", length=4096, status=200) -> Page:
    return Page(status=status, length=length, digest=digest, title=title)


def test_the_same_body_from_the_address_confirms_the_site():
    assert same_site(_page(), _page()) is True


def test_a_page_the_server_wrote_confirms_nothing():
    assert (
        same_site(_page(title="Welcome to nginx!"), _page(title="Welcome to nginx!"))
        is False
    )


def test_a_different_site_on_the_address_is_not_a_confirmation():
    assert same_site(_page(digest="a"), _page(digest="b", title="Other")) is False


def test_the_same_title_at_a_similar_length_confirms():
    assert same_site(_page(digest="a"), _page(digest="b", length=4200)) is True
    assert same_site(_page(digest="a"), _page(digest="b", length=40000)) is False


def test_an_address_that_did_not_answer_confirms_nothing():
    assert same_site(_page(), None) is False
    assert same_site(None, _page()) is False
