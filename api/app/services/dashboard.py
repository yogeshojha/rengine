from uuid import UUID

from sqlalchemy import case, cast, func, select, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.domain_posture import DomainPostureService
from app.services.target_names import target_names
from app.services.target_scope import Targets, keeps
from shared.definitions import domain_posture as posture_defs
from shared.definitions.dashboard import ITEMS_CAP
from shared.definitions.domains import takeover_provider
from shared.models.dashboard import (
    DashboardSignals,
    SpoofableDomain,
    SpoofableSignal,
    TakeoverCandidate,
    TakeoverSignal,
)
from shared.models.subdomain import Subdomain


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def signals(
        self, project_id: UUID, targets: Targets = None
    ) -> DashboardSignals:
        return DashboardSignals(
            takeover=await self._takeover_candidates(project_id, targets),
            spoofable=await self._spoofable_domains(project_id, targets),
        )

    async def _takeover_candidates(
        self, project_id: UUID, targets: Targets = None
    ) -> TakeoverSignal:
        conds = [
            Subdomain.project_id == project_id,
            Subdomain.cname.is_not(None),
            Subdomain.cname != "",
        ]
        if targets is not None:
            conds.append(Subdomain.target_id.in_(targets))
        latest_sighting = (
            select(
                Subdomain.target_id,
                Subdomain.name,
                Subdomain.cname,
                Subdomain.resolved_ips,
                Subdomain.discovered_at,
            )
            .where(*conds)
            .distinct(Subdomain.target_id, Subdomain.name)
            .order_by(
                Subdomain.target_id,
                Subdomain.name,
                Subdomain.discovered_at.desc(),
                Subdomain.scan_id.desc(),
            )
            .subquery()
        )
        ips = cast(latest_sighting.c.resolved_ips, JSONB)
        unresolved = case(
            (func.jsonb_typeof(ips) == "array", func.jsonb_array_length(ips) == 0),
            else_=true(),
        )
        rows = (
            await self.session.execute(select(latest_sighting).where(unresolved))
        ).all()

        candidates: list[TakeoverCandidate] = []
        for r in rows:
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
        candidates.sort(key=lambda c: c.name)
        candidates.sort(key=lambda c: c.last_seen, reverse=True)
        return TakeoverSignal(count=len(candidates), items=candidates[:ITEMS_CAP])

    async def _spoofable_domains(
        self, project_id: UUID, targets: Targets = None
    ) -> SpoofableSignal:
        """Zones whose newest run fails a sender check."""
        hits = [
            hit
            for hit in await DomainPostureService(self.session).spoofable(project_id)
            if keeps(targets, hit[0])
        ]
        if not hits:
            return SpoofableSignal(count=0, items=[])
        names = await target_names(self.session, (tid for tid, *_ in hits))
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
        return SpoofableSignal(count=len(items), items=items[:ITEMS_CAP])
