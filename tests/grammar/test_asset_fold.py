"""Asset predicates fold across OR and must not fold across AND."""

from __future__ import annotations

import pytest

from app.services.subdomain import SubdomainService
from shared.models.subdomain import SubdomainFilter

pytestmark = pytest.mark.grammar


async def _one_host_two_assets(estate, now):
    """One hostname answering on two ports with two different certificates."""
    await estate.scan("example.com", "run", at=now)
    await estate.hosts("run", ["www.example.com"], at=now, status=200)
    await estate.assets(
        "run", ["www.example.com"], at=now, port=443, issuer="CN=Alpha CA"
    )
    await estate.assets(
        "run", ["www.example.com"], at=now, port=8443, issuer="CN=Beta CA"
    )
    return estate.scans["run"]


async def _total(estate, scan, q: str) -> int:
    result = await SubdomainService(estate.session).search(
        estate.project_id, scan, SubdomainFilter(q=q, limit=1)
    )
    assert result.error is None, f"{q}: {result.error}"
    return result.total


async def test_or_over_asset_fields_matches_either_certificate(estate, now):
    scan = await _one_host_two_assets(estate, now)

    assert await _total(estate, scan, 'cert.issuer:"Alpha"') == 1
    assert await _total(estate, scan, 'cert.issuer:"Beta"') == 1
    assert await _total(estate, scan, 'cert.issuer:"Alpha" or cert.issuer:"Beta"') == 1
    assert await _total(estate, scan, 'cert.issuer:"Alpha" or cert.issuer:"Gamma"') == 1
    assert await _total(estate, scan, 'cert.issuer:"Gamma" or cert.issuer:"Delta"') == 0


async def test_and_over_asset_fields_may_match_two_different_assets(estate, now):
    """The reason AND is not folded: one host, two certificates, both conditions true."""
    scan = await _one_host_two_assets(estate, now)

    assert await _total(estate, scan, 'cert.issuer:"Alpha" and cert.issuer:"Beta"') == 1
    assert (
        await _total(estate, scan, 'cert.issuer:"Alpha" and cert.issuer:"Gamma"') == 0
    )


async def test_a_mixed_or_keeps_both_halves(estate, now):
    """An OR of an asset field and a host field must still match on either."""
    scan = await _one_host_two_assets(estate, now)

    assert await _total(estate, scan, 'host:www or cert.issuer:"Gamma"') == 1
    assert await _total(estate, scan, 'host:nothing or cert.issuer:"Alpha"') == 1
    assert await _total(estate, scan, "host:nothing or cert.issuer:nothing") == 0
