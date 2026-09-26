from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa

from shared.definitions.software import Confidence, VersionSource
from shared.models.http_asset import HttpAsset
from shared.models.software import NvdCpeMatch, NvdCve
from shared.models.threat_intel import KevEntry
from shared.services import locks, software_match
from shared.utils.software import version_key
from tools.httpx.parser import parse_httpx_record

pytestmark = pytest.mark.pipeline

CVE = "CVE-2021-23017"
NGINX = [{"name": "Nginx", "version": "1.18.0", "source": VersionSource.BANNER.value}]


async def _corpus(estate) -> None:
    for model in (KevEntry, NvdCpeMatch, NvdCve):
        await estate.session.execute(sa.delete(model).where(model.cve == CVE))
    estate.session.add(NvdCve(cve=CVE, severity="high", cvss_score=7.7))
    estate.session.add(
        NvdCpeMatch(
            cve=CVE,
            vendor="nginx",
            product="nginx",
            version_kind="n",
            end_key=version_key("1.21.0"),
            end_incl=False,
        )
    )
    await estate.session.flush()


async def _software(estate, scan: str, host: str, software: list | None) -> None:
    await estate.session.execute(
        sa.update(HttpAsset)
        .where(HttpAsset.scan_id == estate.scans[scan], HttpAsset.host == host)
        .values(software=software)
    )
    await estate.session.flush()


async def _match(estate, scan: str):
    ids = estate.row_ids(scan)

    def run(session):
        return software_match.match_scan(session, **ids)

    return await estate.session.run_sync(run)


async def _rows(estate, scan: str) -> list:
    result = await estate.session.execute(
        sa.text(
            "SELECT id, xmin::text AS xmin, cve, is_kev, confidence, discovered_at "
            "FROM software_cves WHERE scan_id = :scan_id ORDER BY cve"
        ),
        {"scan_id": str(estate.scans[scan])},
    )
    return result.all()


async def test_a_rematch_leaves_an_unchanged_row_untouched(durable_estate, now):
    estate = durable_estate
    await _corpus(estate)
    await estate.scan("t", "s1", at=now)
    await estate.assets("s1", ["www.example.com"], at=now)
    await _software(estate, "s1", "www.example.com", NGINX)

    first = await _match(estate, "s1")
    assert first.coverage.findings == 1
    assert first.exposed_total == 0
    before = await _rows(estate, "s1")
    assert [r.cve for r in before] == [CVE]
    assert before[0].confidence == Confidence.HIGH.value

    second = await _match(estate, "s1")
    assert second.coverage.findings == 1
    after = await _rows(estate, "s1")
    assert (after[0].id, after[0].xmin, after[0].discovered_at) == (
        before[0].id,
        before[0].xmin,
        before[0].discovered_at,
    )


async def test_moved_intel_updates_the_row_in_place(durable_estate, now):
    estate = durable_estate
    await _corpus(estate)
    await estate.scan("t", "s1", at=now)
    await estate.assets("s1", ["www.example.com"], at=now)
    await _software(estate, "s1", "www.example.com", NGINX)
    await _match(estate, "s1")
    before = await _rows(estate, "s1")

    estate.session.add(KevEntry(cve=CVE, name=CVE, cwes=[]))
    await estate.session.flush()
    await _match(estate, "s1")
    after = await _rows(estate, "s1")
    assert after[0].id == before[0].id
    assert after[0].discovered_at == before[0].discovered_at
    assert after[0].is_kev is True
    assert after[0].xmin != before[0].xmin


async def test_a_component_that_disappears_takes_its_row(durable_estate, now):
    estate = durable_estate
    await _corpus(estate)
    await estate.scan("t", "s1", at=now)
    await estate.assets("s1", ["www.example.com"], at=now)
    await _software(estate, "s1", "www.example.com", NGINX)
    await _match(estate, "s1")
    assert len(await _rows(estate, "s1")) == 1

    await _software(estate, "s1", "www.example.com", [])
    result = await _match(estate, "s1")
    assert result.coverage.findings == 0
    assert await _rows(estate, "s1") == []


async def test_a_new_fingerprint_is_reported_as_exposed(durable_estate, now):
    estate = durable_estate
    await _corpus(estate)
    await estate.scan("t", "s1", at=now)
    await estate.assets("s1", ["a.example.com", "b.example.com"], at=now)
    await _software(estate, "s1", "a.example.com", NGINX)
    await _match(estate, "s1")

    await _software(estate, "s1", "b.example.com", NGINX)
    result = await _match(estate, "s1")
    assert result.exposed_total == 1
    assert [e.host for e in result.exposed] == ["b.example.com"]


async def test_backfill_converges_on_a_versionless_row(durable_estate, now):
    estate = durable_estate
    await estate.scan("t", "s1", at=now)
    await estate.assets("s1", ["www.example.com"], at=now)
    await estate.session.execute(
        sa.update(HttpAsset)
        .where(HttpAsset.scan_id == estate.scans[scan := "s1"])
        .values(software=None, tech=["Apache HTTP Server"], webserver="Apache")
    )
    await estate.session.flush()
    sid = estate.scans[scan]

    assert await estate.session.run_sync(software_match.pending_scans) == [sid]
    filled = await estate.session.run_sync(
        lambda s: software_match.backfill_scan(s, sid)
    )
    assert (filled.rows, filled.components) == (1, 0)
    assert await estate.session.run_sync(software_match.pending_scans) == []
    stored = (
        await estate.session.execute(
            sa.select(HttpAsset.software).where(HttpAsset.scan_id == sid)
        )
    ).scalar_one()
    assert stored == []


def test_the_probe_writes_software_itself() -> None:
    assert "software" in HttpAsset.model_fields
    fields = parse_httpx_record(
        {
            "url": "https://www.example.com",
            "tech": ["Nginx:1.18.0"],
            "webserver": "nginx",
        }
    )
    assert fields["software"] == [
        {
            "name": "Nginx",
            "version": "1.18.0",
            "source": VersionSource.FINGERPRINT.value,
        }
    ]


def test_match_locks_per_scan() -> None:
    a, b = uuid.uuid4(), uuid.uuid4()
    assert locks.software_match(a) == locks.software_match(a)
    assert (
        locks.SOFTWARE_MATCH <= locks.software_match(b) <= locks.SOFTWARE_MATCH + 0xFFFF
    )
