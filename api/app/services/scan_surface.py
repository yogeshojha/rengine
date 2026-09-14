"""What the vulnerability scanner was handed, read back for the UI."""

from __future__ import annotations

from collections import Counter
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions.scan_surface import (
    TIER_LABELS,
    TIER_ORDER,
    DropReason,
    SurfaceClass,
)
from shared.definitions.vulnerabilities import CoverageStatus
from shared.models.scan_surface import (
    AssetSurface,
    ScanSurfaceItem,
    SurfaceSummary,
    SurfaceTierCount,
)
from shared.services.asset_query.scope import QueryScope, ScopeLike

_MAX_UNMAPPED = 12
_RAN = frozenset(
    {
        CoverageStatus.COMPLETED.value,
        CoverageStatus.PARTIAL.value,
        CoverageStatus.FAILED.value,
    }
)


def _outcome(stamp) -> str:
    return str(stamp or "").split("@", 1)[0]


class ScanSurfaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def summary(self, scope: ScopeLike) -> SurfaceSummary:
        scope = QueryScope.of(scope)
        if not scope:
            return SurfaceSummary()
        rows = (
            await self.session.execute(
                select(
                    ScanSurfaceItem.class_,
                    ScanSurfaceItem.drop_reason,
                    ScanSurfaceItem.tiers_planned,
                    ScanSurfaceItem.tiers_done,
                    ScanSurfaceItem.unmapped_tech,
                ).where(scope.match(ScanSurfaceItem.scan_id))
            )
        ).all()
        if not rows:
            return SurfaceSummary()

        summary = SurfaceSummary(planned=True)
        dropped: Counter[str] = Counter()
        unmapped: Counter[str] = Counter()
        tiers: dict[str, SurfaceTierCount] = {}
        for class_, reason, planned, done, missing in rows:
            unmapped.update(missing or [])
            if class_ == SurfaceClass.ROOT.value:
                summary.roots += 1
            elif class_ == SurfaceClass.NAME.value:
                summary.names += 1
            elif class_ == SurfaceClass.SERVICE.value:
                summary.services += 1
            elif class_ == SurfaceClass.REQUEST.value:
                summary.requests += 1
            elif class_ == SurfaceClass.BASE.value:
                summary.bases += 1
            if reason == DropReason.COVERED_BY_ORIGIN.value:
                summary.covered += 1
                continue
            if reason:
                dropped[reason] += 1
                continue
            if class_ == SurfaceClass.ROOT.value:
                summary.origins += 1
            outcomes = dict(done or {})
            for tier in planned or []:
                count = tiers.setdefault(
                    tier, SurfaceTierCount(tier=tier, label=TIER_LABELS.get(tier, tier))
                )
                result = _outcome(outcomes.get(tier))
                if result == CoverageStatus.COMPLETED.value:
                    count.scanned += 1
                elif result in _RAN:
                    count.partial += 1
                else:
                    count.not_scanned += 1
        summary.dropped = dict(dropped)
        summary.tiers = [tiers[t] for t in TIER_ORDER if t in tiers]
        summary.unmapped_tech = [
            name for name, _ in unmapped.most_common(_MAX_UNMAPPED)
        ]
        return summary

    async def for_asset(self, scan_id: UUID, asset_id: UUID) -> AssetSurface | None:
        item = (
            await self.session.execute(
                select(ScanSurfaceItem).where(
                    ScanSurfaceItem.scan_id == scan_id,
                    ScanSurfaceItem.http_asset_id == asset_id,
                    ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
                )
            )
        ).scalar_one_or_none()
        if item is None:
            return None
        representative = None
        if item.representative_id is not None:
            representative = await self.session.scalar(
                select(ScanSurfaceItem.value).where(
                    ScanSurfaceItem.scan_id == scan_id,
                    ScanSurfaceItem.http_asset_id == item.representative_id,
                    ScanSurfaceItem.class_ == SurfaceClass.ROOT.value,
                )
            )
        members = item.members
        if item.representative_id is None and item.cluster_id is not None:
            members = int(
                await self.session.scalar(
                    select(func.count()).where(
                        ScanSurfaceItem.cluster_id == item.cluster_id
                    )
                )
                or 1
            )
        return AssetSurface(
            state=item.state,
            representative_id=item.representative_id,
            representative_value=representative,
            cluster_signals=list(item.cluster_signals or []),
            members=members,
            drop_reason=item.drop_reason,
            tiers_planned=list(item.tiers_planned or []),
            tiers_done=dict(item.tiers_done or {}),
            tags=list(item.tags or []),
            note=item.note,
        )
