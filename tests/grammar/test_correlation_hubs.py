from __future__ import annotations

import pytest

from app.services.correlation_graph import _hubs_of_kind
from shared.definitions.correlation import (
    MAX_HUBS_PER_KIND,
    MIN_ESTATE_FOR_COMMON,
    CorrelationKind,
)

pytestmark = pytest.mark.grammar

CDN = {"151.101.2.132": "fastly"}


def test_a_cdn_address_is_the_provider_not_the_estate():
    hubs = _hubs_of_kind(
        CorrelationKind.IP.value,
        {"151.101.2.132": {0, 1}, "10.0.0.4": {2, 3}},
        CDN,
    )
    by_value = {h.value: h for h in hubs}
    assert by_value["151.101.2.132"].platform
    assert by_value["151.101.2.132"].platform_label == "fastly"
    assert not by_value["10.0.0.4"].platform


def test_a_shared_endpoint_and_a_public_issuer_are_the_provider():
    cname = _hubs_of_kind(
        CorrelationKind.CNAME.value,
        {"j.sni.global.fastly.net": {0, 1}, "lb.internal.example.com": {2, 3}},
        {},
    )
    assert [h.platform for h in cname] == [False, True]

    issuer = _hubs_of_kind(
        CorrelationKind.CERT_ISSUER.value,
        {"CN=E5, O=Let's Encrypt, C=US": {0, 1}, "CN=Example Internal CA": {2, 3}},
        {},
    )
    assert {h.platform_label for h in issuer} == {"", "Let's Encrypt"}


def test_a_share_is_read_against_the_hosts_carrying_the_kind():
    values: dict[str, set[int]] = {"same-body": set(range(MIN_ESTATE_FOR_COMMON))}
    values |= {f"body-{i}": {i} for i in range(100, 115)}
    hubs = _hubs_of_kind(CorrelationKind.BODY.value, values, {})
    (hub,) = [h for h in hubs if h.count > 1]
    assert hub.share == round(MIN_ESTATE_FOR_COMMON / (MIN_ESTATE_FOR_COMMON + 15), 4)
    assert hub.common


def test_a_handful_of_carriers_is_never_common():
    hubs = _hubs_of_kind(CorrelationKind.BODY.value, {"same-body": {0, 1}}, {})
    assert hubs[0].share == 1.0
    assert not hubs[0].common


def test_the_cap_goes_to_the_hubs_that_say_something():
    values = {f"10.0.0.{i}": {i, i + 500} for i in range(MAX_HUBS_PER_KIND)}
    values["151.101.2.132"] = set(range(1000, 1100))
    hubs = _hubs_of_kind(CorrelationKind.IP.value, values, CDN)
    assert len(hubs) == MAX_HUBS_PER_KIND
    assert not any(h.platform for h in hubs)
