from __future__ import annotations

import uuid

import pytest

from app.services.target_estate import TargetEstateService, provider_of
from shared.definitions.estate import EstateReason
from shared.enums.dns import DnsRecordType
from shared.models.dns import DnsLookup, DnsRecord
from shared.models.http_asset import HttpAsset

pytestmark = pytest.mark.api


async def _asset(
    estate,
    scan: str,
    host: str,
    *,
    at,
    final_url: str | None = None,
    location: str | None = None,
    subject: str | None = None,
    sans: list[str] | None = None,
    ip: str | None = None,
    is_cdn: bool = False,
) -> None:
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
            final_url=final_url,
            location=location,
            ip=ip,
            is_cdn=is_cdn,
            tls_fingerprint=uuid.uuid4().hex if sans or subject else None,
            tls_subject_cn=subject,
            tls_sans=sans or [],
            discovered_at=at,
        )
    )
    await estate.session.flush()


async def _dns(estate, value: str, records: list[tuple[str, str]], at) -> None:
    tid = estate.targets[value]
    lookup = DnsLookup(target_id=tid, host=value, queried_at=at)
    estate.session.add(lookup)
    await estate.session.flush()
    for kind, record in records:
        estate.session.add(
            DnsRecord(
                dns_lookup_id=lookup.id,
                target_id=tid,
                record_type=DnsRecordType(kind),
                value=record,
            )
        )
    await estate.session.flush()


async def _estate(estate, value: str, scan: str):
    return await TargetEstateService(estate.session).for_target(
        estate.project_id, estate.targets[value], estate.scans[scan]
    )


def _signals(out, domain: str) -> list[str]:
    row = next((d for d in out.domains if d.domain == domain), None)
    return [s.kind for s in row.signals] if row else []


async def test_a_redirect_into_another_domain_is_a_relative(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await _asset(
        estate,
        "a",
        "www.financialombudsman.gov.cy",
        at=now,
        final_url="https://financialombudsman.org.cy/",
    )
    await _asset(estate, "a", "apply.gov.cy", at=now, location="https://1.2.3.4/")

    out = await _estate(estate, "gov.cy", "a")

    assert _signals(out, "financialombudsman.org.cy") == [EstateReason.REDIRECT.value]
    assert out.counts.untracked == 1
    assert all(d.domain != "1.2.3.4" for d in out.domains)


async def test_a_cname_into_a_platform_is_a_provider_not_a_relative(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await estate.hosts("a", ["www.gov.cy"], at=now, cname="portal-prod.a03.azurefd.net")
    await estate.hosts("a", ["eas.capo.gov.cy"], at=now, cname="eas.x.hdsec.xyz")

    out = await _estate(estate, "gov.cy", "a")

    assert _signals(out, "hdsec.xyz") == [EstateReason.CNAME.value]
    assert [(p.name, p.kind) for p in out.providers] == [("Azure Front Door", "edge")]
    assert out.providers[0].query == "cname:azurefd.net"


async def test_a_certificate_for_another_organisation_is_direct_evidence(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await _asset(
        estate,
        "a",
        "eforms.moec.gov.cy",
        at=now,
        subject="*.schools.ac.cy",
        sans=["*.schools.ac.cy", "schools.ac.cy"],
    )

    out = await _estate(estate, "gov.cy", "a")

    assert _signals(out, "schools.ac.cy") == [EstateReason.CERT_SUBJECT.value]
    assert out.neighbours == []


async def test_a_platform_certificate_makes_neighbours_not_relatives(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    tenants = [f"tenant{i}.example{i}.com" for i in range(8)]
    await _asset(
        estate,
        "a",
        "helpdesk.gov.cy",
        at=now,
        subject="servicedesk.vendor.ie",
        sans=[*tenants, "helpdesk.gov.cy"],
    )

    out = await _estate(estate, "gov.cy", "a")

    assert out.domains == []
    assert [n.subject for n in out.neighbours] == ["servicedesk.vendor.ie"]
    assert out.neighbours[0].names == 8
    assert out.counts.neighbour_names == 8


async def test_a_name_on_the_targets_own_certificate_is_a_relative(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await _asset(
        estate,
        "a",
        "cyprus-tomorrow.gov.cy",
        at=now,
        subject="cyprus-tomorrow.gov.cy",
        sans=["cyprus-tomorrow.gov.cy", "childcom.org.cy"],
    )

    out = await _estate(estate, "gov.cy", "a")

    assert _signals(out, "childcom.org.cy") == [EstateReason.CERT_SAN.value]


async def test_a_tracked_domain_is_marked_and_ranked_after_candidates(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await estate.scan("childcom.org.cy", "b", at=now)
    await _asset(
        estate,
        "a",
        "www.gov.cy",
        at=now,
        final_url="https://childcom.org.cy/",
    )
    await _asset(estate, "a", "x.gov.cy", at=now, final_url="https://other.cy/")

    out = await _estate(estate, "gov.cy", "a")

    tracked = next(d for d in out.domains if d.domain == "childcom.org.cy")
    assert tracked.target_id == estate.targets["childcom.org.cy"]
    assert [d.domain for d in out.domains] == ["other.cy", "childcom.org.cy"]
    assert out.counts.tracked == 1


async def test_dns_records_name_providers_and_own_infrastructure(estate, now):
    await estate.scan("gov.cy", "a", at=now)
    await _dns(
        estate,
        "gov.cy",
        [
            ("NS", "ns01.gov.cy"),
            ("NS", "dns41.cloudns.net"),
            ("MX", "mail03.gov.cy"),
            (
                "TXT",
                "v=spf1 ip4:212.31.118.0/24 include:spf.protection.outlook.com -all",
            ),
        ],
        now,
    )

    out = await _estate(estate, "gov.cy", "a")

    assert sorted(out.own) == ["212.31.118.0/24", "mail03.gov.cy", "ns01.gov.cy"]
    assert {(p.name, p.kind) for p in out.providers} == {
        ("ClouDNS", "dns"),
        ("Microsoft 365", "mail"),
    }


async def test_the_project_estate_merges_candidates_across_targets(estate, now):
    await estate.scan("one.cy", "a", at=now)
    await estate.scan("two.cy", "b", at=now)
    await estate.hosts("a", ["www.one.cy"], at=now)
    await estate.hosts("b", ["www.two.cy", "x.two.cy"], at=now)
    await _asset(estate, "a", "www.one.cy", at=now, final_url="https://shared.cy/")
    await _asset(estate, "b", "www.two.cy", at=now, final_url="https://shared.cy/")
    await _asset(estate, "b", "x.two.cy", at=now, final_url="https://only.cy/")

    out = await TargetEstateService(estate.session).for_project(estate.project_id)

    assert out.targets_examined == 2
    assert [d.domain for d in out.domains] == ["shared.cy", "only.cy"]
    assert sorted(s.target_value for s in out.domains[0].sources) == [
        "one.cy",
        "two.cy",
    ]


def test_provider_names_come_from_the_suffix_map():
    assert provider_of("dsf-prod.a03.azurefd.net") == "Azure Front Door"
    assert provider_of("j.sni.global.fastly.net") == "Fastly"
    assert provider_of("leela.connectit.gr") is None


async def test_names_under_a_registry_target_are_its_own(estate, now):
    await estate.scan("go.id", "a", at=now)
    await _asset(
        estate, "a", "www.go.id", at=now, final_url="https://kemenperin.go.id/"
    )
    await _asset(estate, "a", "x.go.id", at=now, final_url="https://desa.id/")

    out = await _estate(estate, "go.id", "a")

    assert [d.domain for d in out.domains] == ["desa.id"]
