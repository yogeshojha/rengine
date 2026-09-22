from __future__ import annotations

import pytest

from shared.services.origin_exposure import (
    ORIGIN_EXPOSED,
    OriginExposureService,
    _Asset,
)

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
