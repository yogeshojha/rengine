from __future__ import annotations

import pytest
from sqlalchemy import select

from shared.enums.ip import IpSource
from shared.enums.target import TargetType
from shared.models.ip_address import IpAddress
from shared.services.scan_resolve import ResolvedScanConfig
from stages.base import StageContext
from stages.seed_resolution.stage import SeedResolutionStage

pytestmark = pytest.mark.pipeline


def _expansion(ip: str) -> dict:
    return {
        "ip": ip,
        "version": 4,
        "source": IpSource.CIDR_EXPANSION.value,
        "prefix": "203.0.113.0/24",
        "asn": None,
    }


async def test_an_expansion_keeps_the_addresses_asset_seed_wrote(durable_estate, now):
    estate = durable_estate
    sid = await estate.scan("203.0.113.0/24", "run", at=now)
    tid = estate.targets["203.0.113.0/24"]
    estate.session.add(
        IpAddress(
            project_id=estate.project_id,
            scan_id=sid,
            target_id=tid,
            ip="203.0.113.7",
            version=4,
            source=IpSource.SEED.value,
        )
    )
    await estate.session.commit()

    def write(sync_session) -> int:
        stage = SeedResolutionStage.__new__(SeedResolutionStage)
        stage.session = sync_session
        stage.ctx = StageContext(
            scan_id=sid,
            target_id=tid,
            project_id=estate.project_id,
            target_value="203.0.113.0/24",
            target_type=TargetType.IP_RANGE.value,
            resolved=ResolvedScanConfig(
                target_value="203.0.113.0/24", target_type=TargetType.IP_RANGE.value
            ),
        )
        return stage._persist(
            [
                _expansion("203.0.113.7"),
                _expansion("203.0.113.8"),
                _expansion("203.0.113.8"),
            ]
        )

    assert await estate.session.run_sync(write) == 2

    rows = (
        await estate.session.execute(
            select(IpAddress.ip, IpAddress.source, IpAddress.prefix)
            .where(IpAddress.scan_id == sid)
            .order_by(IpAddress.ip)
        )
    ).all()
    assert [tuple(r) for r in rows] == [
        ("203.0.113.7", IpSource.SEED.value, "203.0.113.0/24"),
        ("203.0.113.8", IpSource.CIDR_EXPANSION.value, "203.0.113.0/24"),
    ]
