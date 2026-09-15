from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query.predicates import live
from app.services.dashboard_overview import (
    VULNS,
    WEB,
    DashboardOverviewService,
    _act,
    _suppressed,
)
from shared.definitions.vulnerabilities import (
    ACTIONABLE_SEVERITIES,
    coerce_severity,
)
from shared.models.dashboard import DashboardSurfaceRisk, SurfaceRiskTarget
from shared.models.scan import Scan
from shared.models.subdomain import Subdomain
from shared.models.tag import TargetTag
from shared.models.target import Target, TargetOrganization
from shared.models.vulnerability import Vulnerability
from shared.utils.datetime import utc_now


class SurfaceRiskService:
    """Live web assets against open findings, per target."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.overview = DashboardOverviewService(session)

    async def rows(
        self,
        project_id: UUID,
        organization_id: UUID | None = None,
        tag_id: UUID | None = None,
    ) -> DashboardSurfaceRisk:
        targets = await self._targets(project_id, organization_id, tag_id)
        out = DashboardSurfaceRisk(targets_total=len(targets))
        if not targets:
            return out
        ids = {t.id for t in targets}
        runs_by_target, _ = await self.overview._runs(project_id, utc_now())
        runs_by_target = {k: v for k, v in runs_by_target.items() if k in ids}
        scans: dict[UUID, Scan] = {
            s.id: s for runs in runs_by_target.values() for s in runs
        }
        counts = await self.overview._counts(list(scans))
        ran = await self.overview._ran(list(scans))
        covered = self.overview._covered(runs_by_target, counts, ran)
        web_cover = {tid: ids[0] for tid, ids in covered[WEB].items() if ids}
        vuln_cover = {tid: ids[0] for tid, ids in covered[VULNS].items() if ids}

        live_by_scan = await self._live(list(web_cover.values()))
        findings = await self._findings(list(vuln_cover.values()))
        orgs, tags = await self._labels(list(ids))

        for t in targets:
            runs = runs_by_target.get(t.id)
            if not runs:
                continue
            latest = runs[0]
            web_id = web_cover.get(t.id)
            vuln_id = vuln_cover.get(t.id)
            sev = findings["sev"].get(vuln_id, {}) if vuln_id else {}
            row = SurfaceRiskTarget(
                target_id=t.id,
                target_value=t.target_value,
                target_type=t.target_type.value,
                names=counts[WEB].get(web_id, (0, None))[0] if web_id else 0,
                live=live_by_scan.get(web_id, 0) if web_id else 0,
                findings=sum(sev.values()),
                actionable=sum(sev.get(s, 0) for s in ACTIONABLE_SEVERITIES),
                act=findings["act"].get(vuln_id, 0) if vuln_id else 0,
                kev=findings["kev"].get(vuln_id, 0) if vuln_id else 0,
                by_severity=sev,
                scan_id=latest.id,
                scan_status=latest.status,
                last_at=latest.completed_at or latest.started_at or latest.created_at,
                organizations=orgs.get(t.id, []),
                tags=tags.get(t.id, []),
            )
            out.rows.append(row)

        out.rows.sort(key=lambda r: (-r.findings, -r.live, r.target_value))
        out.scanned = len(out.rows)
        out.live = sum(r.live for r in out.rows)
        out.findings = sum(r.findings for r in out.rows)
        out.actionable = sum(r.actionable for r in out.rows)
        out.act = sum(r.act for r in out.rows)
        return out

    async def _targets(
        self, project_id: UUID, organization_id: UUID | None, tag_id: UUID | None
    ) -> list[Target]:
        query = (
            select(Target)
            .where(Target.project_id == project_id)
            .order_by(Target.target_value.asc())
        )
        if organization_id:
            query = query.join(
                TargetOrganization,
                and_(
                    TargetOrganization.target_id == Target.id,
                    TargetOrganization.organization_id == organization_id,
                ),
            )
        if tag_id:
            query = query.join(
                TargetTag,
                and_(TargetTag.target_id == Target.id, TargetTag.tag_id == tag_id),
            )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def _live(self, scan_ids: list[UUID]) -> dict[UUID, int]:
        if not scan_ids:
            return {}
        result = await self.session.execute(
            select(Subdomain.scan_id, func.count())
            .where(Subdomain.scan_id.in_(scan_ids), live())
            .group_by(Subdomain.scan_id)
        )
        return {row[0]: int(row[1]) for row in result.all()}

    async def _findings(self, scan_ids: list[UUID]) -> dict[str, dict]:
        out: dict[str, dict] = {"sev": {}, "act": {}, "kev": {}}
        if not scan_ids:
            return out
        open_rows = and_(Vulnerability.scan_id.in_(scan_ids), not_(_suppressed()))
        rows = await self.session.execute(
            select(Vulnerability.scan_id, Vulnerability.severity, func.count())
            .where(open_rows)
            .group_by(Vulnerability.scan_id, Vulnerability.severity)
        )
        sev: dict[UUID, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for scan_id, severity, n in rows.all():
            sev[scan_id][coerce_severity(severity)] += int(n)
        out["sev"] = {k: dict(v) for k, v in sev.items()}
        tiers = await self.session.execute(
            select(
                Vulnerability.scan_id,
                func.count().filter(_act()),
                func.count().filter(Vulnerability.is_kev.is_(True)),
            )
            .where(open_rows)
            .group_by(Vulnerability.scan_id)
        )
        for scan_id, act, kev in tiers.all():
            out["act"][scan_id] = int(act or 0)
            out["kev"][scan_id] = int(kev or 0)
        return out

    async def _labels(
        self, target_ids: list[UUID]
    ) -> tuple[dict[UUID, list[UUID]], dict[UUID, list[UUID]]]:
        orgs: dict[UUID, list[UUID]] = defaultdict(list)
        tags: dict[UUID, list[UUID]] = defaultdict(list)
        result = await self.session.execute(
            select(
                TargetOrganization.target_id, TargetOrganization.organization_id
            ).where(TargetOrganization.target_id.in_(target_ids))
        )
        for tid, oid in result.all():
            orgs[tid].append(oid)
        result = await self.session.execute(
            select(TargetTag.target_id, TargetTag.tag_id).where(
                TargetTag.target_id.in_(target_ids)
            )
        )
        for tid, gid in result.all():
            tags[tid].append(gid)
        return orgs, tags
