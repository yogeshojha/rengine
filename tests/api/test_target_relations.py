from __future__ import annotations

import uuid

import pytest

from app.services.target_relations import TargetRelationService, _dns_keys
from shared.definitions.relations import TargetRelation
from shared.enums.ip import IpSource
from shared.enums.whois import WhoisLookupType
from shared.models.http_asset import HttpAsset
from shared.models.ip_address import IpAddress
from shared.models.target import Target
from shared.models.whois import WhoisRecord

pytestmark = pytest.mark.api


async def _address(estate, scan: str, ip: str, asn: int, org: str, at) -> None:
    sid = estate.scans[scan]
    estate.session.add(
        IpAddress(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=await estate._target_of(sid),
            ip=ip,
            version=4,
            source=IpSource.DNS_RESOLUTION.value,
            asn=asn,
            asn_org=org,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _certificate(estate, scan: str, host: str, sans: list[str], at) -> None:
    sid = estate.scans[scan]
    estate.session.add(
        HttpAsset(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=await estate._target_of(sid),
            url=f"https://{host}",
            host=host,
            port=443,
            status_code=200,
            tls_fingerprint=uuid.uuid4().hex,
            tls_sans=sans,
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _registrant(estate, value: str, name: str, at) -> None:
    record = WhoisRecord(
        query_value=value,
        lookup_type=WhoisLookupType.DOMAIN,
        queried_at=at,
        registrant_name=name,
    )
    estate.session.add(record)
    await estate.session.flush()
    target = await estate.session.get(Target, estate.targets[value])
    target.whois_record_id = record.id
    await estate.session.flush()


async def _related(estate, value: str):
    rows = await TargetRelationService(estate.session).for_target(
        estate.project_id, estate.targets[value]
    )
    return {item.target_value: [r.kind for r in item.reasons] for item in rows.items}


async def test_a_landlords_network_is_not_a_relation(estate, now):
    await estate.scan("one.com", "a", at=now)
    await estate.scan("two.com", "b", at=now)
    await _address(estate, "a", "3.1.1.1", 16509, "Amazon.com, Inc.", now)
    await _address(estate, "b", "3.1.1.2", 16509, "Amazon.com, Inc.", now)

    assert await _related(estate, "one.com") == {}


async def test_a_network_the_organisation_runs_is_a_relation(estate, now):
    await estate.scan("uber.com", "a", at=now)
    await estate.scan("ubereats.com", "b", at=now)
    await _address(estate, "a", "69.48.216.1", 63086, "Uber Technologies, Inc", now)
    await _address(estate, "b", "69.48.216.2", 63086, "Uber Technologies, Inc", now)

    assert await _related(estate, "uber.com") == {
        "ubereats.com": [TargetRelation.NETWORK.value]
    }


async def test_a_certificate_naming_the_other_target_is_a_relation(estate, now):
    await estate.scan("one.com", "a", at=now)
    await estate.hosts("a", ["www.one.com"], at=now, status=200)
    await estate.target("two.com")
    await _certificate(estate, "a", "www.one.com", ["www.one.com", "shop.two.com"], now)

    assert await _related(estate, "one.com") == {
        "two.com": [TargetRelation.CERTIFICATE.value]
    }


async def test_one_registrant_spelled_two_ways_is_a_relation(estate, now):
    await estate.target("one.com")
    await estate.target("two.com")
    await _registrant(estate, "one.com", "Example Holdings Inc.", now)
    await _registrant(estate, "two.com", "example holdings, inc", now)

    assert await _related(estate, "one.com") == {
        "two.com": [TargetRelation.REGISTRANT.value]
    }


OWNED = {"acme.com", "acme.io"}


def test_a_rented_mail_host_says_nothing():
    assert _dns_keys("MX", "alt1.aspmx.l.google.com", "", set(), OWNED) == []
    assert _dns_keys("MX", "mx.zendesk.com", "", set(), OWNED) == []


def test_a_mail_host_the_estate_owns_is_a_fact():
    assert _dns_keys("MX", "mail.acme.com", "", set(), OWNED) == [
        ("MX mail.acme.com", "mx:mail.acme.com")
    ]


def test_an_spf_include_counts_only_for_the_estate_own_domain():
    spf = "v=spf1 include:_spf.google.com include:mail.zendesk.com include:_spf.acme.io -all"
    assert _dns_keys("TXT", spf, "", set(), OWNED) == [
        ("SPF include:_spf.acme.io", "spf:_spf.acme.io")
    ]


def test_a_zone_contact_is_read_from_the_soa():
    assert _dns_keys("SOA", "ns1.acme.com", "hostmaster.acme.com", set(), OWNED) == [
        ("SOA hostmaster.acme.com", "soa:hostmaster.acme.com")
    ]
    assert (
        _dns_keys(
            "SOA", "ns-1.awsdns-50.org", "awsdns-hostmaster.amazon.com", set(), OWNED
        )
        == []
    )


def test_an_edge_address_is_not_a_shared_machine():
    assert _dns_keys("A", "203.0.113.9", "", set(), OWNED) == [
        ("A 203.0.113.9", "address:203.0.113.9")
    ]
    assert _dns_keys("A", "151.101.2.132", "", {"151.101.2.132"}, OWNED) == []


def test_a_nameserver_record_is_left_to_the_whois_relation():
    assert _dns_keys("NS", "a.ns.acme.com", "", set(), OWNED) == []
