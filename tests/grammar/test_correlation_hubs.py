from __future__ import annotations

import uuid

import pytest

from shared.definitions.correlation import (
    MIN_ESTATE_FOR_COMMON,
    CorrelationKind,
)
from shared.services.correlation.hubs import (
    CorrelationFinder,
    Hub,
    Member,
    _written_by,
)
from shared.services.correlation.kinds import platform_for

pytestmark = pytest.mark.grammar

CDN = {"151.101.2.132": "fastly"}


def member(
    name: str,
    *,
    status: int | None = 200,
    title: str | None = "Acme Console",
    cname: str | None = None,
) -> Member:
    return Member(uuid.uuid4(), name, uuid.uuid4(), status, True, title, cname)


def hub(kind: str, value: str, hosts: int, carriers: int, targets: int = 1) -> Hub:
    return Hub(kind=kind, value=value, hosts=hosts, carriers=carriers, targets=targets)


def test_a_cdn_address_is_the_provider_not_the_estate():
    assert platform_for(CorrelationKind.IP.value, "151.101.2.132", CDN) == "fastly"
    assert platform_for(CorrelationKind.IP.value, "10.0.0.4", CDN) == ""


def test_a_shared_endpoint_and_a_public_issuer_are_the_provider():
    assert (
        platform_for(CorrelationKind.CNAME.value, "j.sni.global.fastly.net", {})
        == "Fastly"
    )
    assert (
        platform_for(CorrelationKind.CNAME.value, "lb.internal.example.com", {}) == ""
    )
    assert (
        platform_for(
            CorrelationKind.CERT_ISSUER.value, "CN=E5, O=Let's Encrypt, C=US", {}
        )
        == "Let's Encrypt"
    )
    assert (
        platform_for(CorrelationKind.CERT_ISSUER.value, "CN=Example Internal CA", {})
        == ""
    )


def test_a_share_is_read_against_the_hosts_carrying_the_kind():
    carriers = MIN_ESTATE_FOR_COMMON + 15
    found = hub(
        CorrelationKind.BODY.value, "same-body", MIN_ESTATE_FOR_COMMON, carriers
    )
    assert round(found.share, 4) == round(MIN_ESTATE_FOR_COMMON / carriers, 4)
    assert found.common


def test_a_handful_of_carriers_is_never_common():
    found = hub(CorrelationKind.BODY.value, "same-body", 2, 2)
    assert found.share == 1.0
    assert not found.common


def test_a_title_restating_the_status_is_the_servers():
    found = hub(CorrelationKind.TITLE.value, "404 Not Found", 3, 40)
    found.members = [
        member(f"h{i}", status=404, title="404 Not Found") for i in range(3)
    ]
    assert _written_by(found) == "the server"


def test_a_title_the_application_wrote_is_its_own():
    found = hub(CorrelationKind.TITLE.value, "Acme Console", 3, 40)
    found.members = [member(f"h{i}") for i in range(3)]
    assert _written_by(found) == ""


def test_an_identity_carried_only_on_a_shared_edge_is_the_platforms():
    found = hub(CorrelationKind.CERT.value, "aa:bb", 2, 40)
    found.members = [member(f"h{i}", cname="j.sni.global.fastly.net") for i in range(2)]
    assert _written_by(found) == "Fastly"


def test_crossing_targets_outranks_a_bigger_hub_inside_one():
    wide = hub(CorrelationKind.TITLE.value, "wide", 200, 4000, targets=1)
    crossing = hub(CorrelationKind.TITLE.value, "crossing", 4, 4000, targets=3)
    ranked = sorted([wide, crossing], key=lambda h: CorrelationFinder._rank(h, True))
    assert [h.value for h in ranked] == ["crossing", "wide"]
    ranked = sorted([wide, crossing], key=lambda h: CorrelationFinder._rank(h, False))
    assert [h.value for h in ranked] == ["wide", "crossing"]


def test_a_provider_hub_ranks_last_whatever_its_size():
    provider = hub(CorrelationKind.IP.value, "151.101.2.132", 500, 600)
    provider.platform = "fastly"
    own = hub(CorrelationKind.IP.value, "10.0.0.4", 2, 600)
    ranked = sorted([provider, own], key=lambda h: CorrelationFinder._rank(h, False))
    assert [h.value for h in ranked] == ["10.0.0.4", "151.101.2.132"]
