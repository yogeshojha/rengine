"""A prefix is filled only when the feed's range is exactly one network."""

from __future__ import annotations

import ipaddress

import pytest
import sqlalchemy as sa

from shared.enums.ip import IpSource
from shared.models.ip_address import IpAddress
from shared.services.ip_asn import enrich_addresses

pytestmark = pytest.mark.pipeline


async def _ranges(estate, rows: list[tuple[str, str, int, str]]) -> None:
    await estate.session.execute(
        sa.text(
            "INSERT INTO ip_asn_ranges (start_ip, end_ip, asn, as_name) "
            "VALUES (cast(:s as inet), cast(:e as inet), :a, :n)"
        ),
        [{"s": s, "e": e, "a": a, "n": n} for s, e, a, n in rows],
    )
    await estate.session.execute(
        sa.text(
            "INSERT INTO ip_country_ranges (start_ip, end_ip, country) "
            "VALUES (cast('1.0.0.0' as inet), cast('223.255.255.255' as inet), 'US')"
        )
    )
    await estate.session.flush()


async def _address(estate, scan: str, ip: str) -> None:
    estate.session.add(
        IpAddress(
            project_id=estate.project_id,
            scan_id=estate.scans[scan],
            target_id=await estate._target_of(estate.scans[scan]),
            ip=ip,
            source=IpSource.DNS_RESOLUTION.value,
        )
    )
    await estate.session.flush()


async def _enrich(estate, scan: str) -> int:
    sid = estate.scans[scan]
    return await estate.session.run_sync(
        lambda s: enrich_addresses(s, scan_id=sid, only_missing=False)
    )


async def _row(estate, ip: str) -> IpAddress:
    return await estate.session.scalar(sa.select(IpAddress).where(IpAddress.ip == ip))


async def test_a_range_that_is_one_network_fills_the_prefix(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _ranges(estate, [("203.0.113.0", "203.0.113.255", 64500, "Example Net")])
    await _address(estate, "run", "203.0.113.7")

    assert await _enrich(estate, "run") == 1

    row = await _row(estate, "203.0.113.7")
    assert row.asn == 64500
    assert row.prefix == "203.0.113.0/24"


async def test_an_aggregated_range_leaves_the_prefix_unknown(estate, now):
    """inet_merge would report a /17 for a range that is not one — a null is honest."""
    await estate.scan("example.com", "run", at=now)
    await _ranges(estate, [("198.51.100.0", "198.51.196.255", 64501, "Aggregate")])
    await _address(estate, "run", "198.51.100.9")

    await _enrich(estate, "run")

    row = await _row(estate, "198.51.100.9")
    assert row.asn == 64501, "the ASN is still known"
    assert row.prefix is None, "the prefix is not"


async def test_a_filled_prefix_always_contains_its_address(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _ranges(
        estate,
        [
            ("203.0.113.0", "203.0.113.255", 64500, "Slash 24"),
            ("192.0.2.0", "192.0.2.127", 64502, "Slash 25"),
        ],
    )
    for ip in ("203.0.113.200", "192.0.2.3"):
        await _address(estate, "run", ip)

    await _enrich(estate, "run")

    for ip in ("203.0.113.200", "192.0.2.3"):
        row = await _row(estate, ip)
        assert row.prefix is not None
        assert ipaddress.ip_address(ip) in ipaddress.ip_network(row.prefix)


async def test_an_address_outside_every_range_gets_nothing(estate, now):
    await estate.scan("example.com", "run", at=now)
    await _ranges(estate, [("203.0.113.0", "203.0.113.255", 64500, "Example Net")])
    await _address(estate, "run", "10.99.0.1")

    await _enrich(estate, "run")

    row = await _row(estate, "10.99.0.1")
    assert row.asn is None
    assert row.prefix is None
