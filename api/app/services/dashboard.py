from datetime import timedelta
from uuid import UUID

from sqlalchemy import Row, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.domain_posture import DomainPostureService
from shared.definitions import domain_posture as posture_defs
from shared.definitions.domains import takeover_provider
from shared.enums.scan import ScanStatus
from shared.enums.target import TargetType
from shared.logging import get_logger
from shared.models.dashboard import (
    DashboardSignals,
    SpoofableDomain,
    SpoofableSignal,
    StaleSignal,
    StaleTarget,
    TakeoverCandidate,
    TakeoverSignal,
)
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.utils.datetime import utc_now

logger = get_logger(__name__)

_CNAME_SCAN_CAP = 50000
_ITEMS_CAP = 100
_STALE_DAYS = 30

_DOMAIN_TYPES = (TargetType.DOMAIN, TargetType.URL)


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def signals(self, project_id: UUID) -> DashboardSignals:
        return DashboardSignals(
            takeover=await self._takeover_candidates(project_id),
            spoofable=await self._spoofable_domains(project_id),
            stale=await self._stale_targets(project_id),
        )

    async def _takeover_candidates(self, project_id: UUID) -> TakeoverSignal:
        query = (
            select(
                Subdomain.target_id,
                Subdomain.name,
                Subdomain.cname,
                Subdomain.resolved_ips,
                Subdomain.discovered_at,
                Subdomain.scan_id,
            )
            .where(
                Subdomain.project_id == project_id,
                Subdomain.cname.is_not(None),
                Subdomain.cname != "",
            )
            .order_by(Subdomain.discovered_at.desc(), Subdomain.scan_id.desc())
            .limit(_CNAME_SCAN_CAP + 1)
        )
        rows = list((await self.session.execute(query)).all())
        if len(rows) > _CNAME_SCAN_CAP:
            logger.warning("takeover scan capped at %d cname rows", _CNAME_SCAN_CAP)
            rows = rows[:_CNAME_SCAN_CAP]
        rows.sort(key=lambda r: (r.discovered_at, str(r.scan_id)))
        latest: dict[tuple, Row] = {}
        for r in rows:
            latest[(r.target_id, r.name)] = r

        candidates: list[TakeoverCandidate] = []
        for r in latest.values():
            if r.resolved_ips:
                continue
            provider = takeover_provider(r.cname or "")
            if provider is None:
                continue
            candidates.append(
                TakeoverCandidate(
                    name=r.name,
                    target_id=r.target_id,
                    cname=r.cname,
                    provider=provider,
                    last_seen=r.discovered_at,
                )
            )
        candidates.sort(key=lambda c: c.last_seen, reverse=True)
        return TakeoverSignal(count=len(candidates), items=candidates[:_ITEMS_CAP])

    async def _spoofable_domains(self, project_id: UUID) -> SpoofableSignal:
        """Zones whose newest run fails a sender check."""
        hits = await DomainPostureService(self.session).spoofable(project_id)
        if not hits:
            return SpoofableSignal(count=0, items=[])
        names = dict(
            (
                await self.session.execute(
                    select(Target.id, Target.target_value).where(
                        Target.id.in_({tid for tid, *_ in hits})
                    )
                )
            ).all()
        )
        items = [
            SpoofableDomain(
                target_id=tid,
                target_value=names.get(tid, zone),
                zone=zone,
                reason=posture_defs.CHECK_BY_KEY[key].label,
                check=key,
            )
            for tid, zone, key, _at in hits
            if tid in names
        ]
        items.sort(key=lambda d: (d.zone, d.target_value))
        return SpoofableSignal(count=len(items), items=items[:_ITEMS_CAP])

    async def _stale_targets(self, project_id: UUID) -> StaleSignal:
        cutoff = utc_now() - timedelta(days=_STALE_DAYS)
        last_completed = (
            select(
                Scan.target_id.label("tid"),
                func.max(func.coalesce(Scan.completed_at, Scan.started_at)).label(
                    "last"
                ),
            )
            .where(
                Scan.project_id == project_id,
                Scan.status == ScanStatus.COMPLETED.value,
            )
            .group_by(Scan.target_id)
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(
                    Target.id,
                    Target.target_value,
                    Target.target_type,
                    last_completed.c.last,
                )
                .join(last_completed, last_completed.c.tid == Target.id, isouter=True)
                .where(Target.project_id == project_id)
            )
        ).all()

        never: list[StaleTarget] = []
        stale: list[StaleTarget] = []
        for tid, value, ttype, last in rows:
            tt = getattr(ttype, "value", ttype)
            if last is None:
                never.append(
                    StaleTarget(
                        target_id=tid,
                        target_value=value,
                        target_type=tt,
                        last_scanned_at=None,
                    )
                )
            elif last < cutoff:
                stale.append(
                    StaleTarget(
                        target_id=tid,
                        target_value=value,
                        target_type=tt,
                        last_scanned_at=last,
                    )
                )
        never.sort(key=lambda t: t.target_value)
        stale.sort(key=lambda t: t.last_scanned_at or utc_now())
        items = (never + stale)[:_ITEMS_CAP]
        return StaleSignal(never_scanned=len(never), stale=len(stale), items=items)
