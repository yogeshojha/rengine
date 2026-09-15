"""Domain posture over one scan, one target, or every target's latest run."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import array as pg_array
from sqlalchemy.ext.asyncio import AsyncSession

from shared.definitions import domain_posture as defs
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.models.domain_posture import (
    DomainPosture,
    DomainPostureRead,
    DomainPostureSummary,
    PostureCheckCount,
)
from shared.models.scan import Scan
from shared.services.asset_query import QueryScope, ScopeLike
from shared.services.scan_scope import census_only

MAX_ZONES = 500


def _read(row: DomainPosture) -> DomainPostureRead:
    return DomainPostureRead(
        id=row.id,
        scan_id=row.scan_id,
        target_id=row.target_id,
        zone=row.zone,
        parent=row.parent,
        hosts=row.hosts,
        spf=row.spf,
        spf_all=row.spf_all,
        spf_lookups=row.spf_lookups,
        dmarc=row.dmarc,
        dmarc_policy=row.dmarc_policy,
        dmarc_subdomain_policy=row.dmarc_subdomain_policy,
        dmarc_pct=row.dmarc_pct,
        dmarc_rua=row.dmarc_rua,
        dmarc_inherited=row.dmarc_inherited,
        dkim_selectors=list(row.dkim_selectors or []),
        dkim_key_bits=row.dkim_key_bits,
        mx=list(row.mx or []),
        null_mx=row.null_mx,
        mta_sts=row.mta_sts,
        mta_sts_mode=row.mta_sts_mode,
        tls_rpt=row.tls_rpt,
        dnssec=row.dnssec,
        caa=list(row.caa or []),
        posture_issues=list(row.posture_issues or []),
        posture_checked=list(row.posture_checked or []),
        evidence=dict(row.evidence or {}),
        discovered_at=row.discovered_at,
    )


def _summarise(rows: list[DomainPosture]) -> DomainPostureSummary:
    warning_keys = set(defs.WARNING_KEYS)
    spoofable_keys = set(defs.SPOOFABLE_KEYS)
    failing: dict[str, int] = dict.fromkeys(defs.CHECK_KEYS, 0)
    applicable: dict[str, int] = dict.fromkeys(defs.CHECK_KEYS, 0)
    warning = info = clean = spoofable = hosts = 0
    for row in rows:
        issues = set(row.posture_issues or [])
        for key in row.posture_checked or []:
            if key in applicable:
                applicable[key] += 1
        for key in issues:
            if key in failing:
                failing[key] += 1
        if issues & warning_keys:
            warning += 1
        elif issues:
            info += 1
        else:
            clean += 1
        if issues & spoofable_keys:
            spoofable += 1
        hosts += row.hosts
    ordered = sorted(
        rows,
        key=lambda r: (
            -len(set(r.posture_issues or []) & warning_keys),
            -r.hosts,
            r.zone,
        ),
    )
    return DomainPostureSummary(
        covered=bool(rows),
        zones=[_read(r) for r in ordered[:MAX_ZONES]],
        evaluated=len(rows),
        clean=clean,
        warning=warning,
        info=info,
        spoofable=spoofable,
        hosts=hosts,
        checks=[
            PostureCheckCount(
                key=spec.key,
                failing=failing[spec.key],
                applicable=applicable[spec.key],
                query=spec.query,
            )
            for spec in defs.CHECKS
        ],
    )


class DomainPostureService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def summary(self, project_id: UUID, scope: ScopeLike) -> DomainPostureSummary:
        """Zones of the scope, one row each."""
        scope = QueryScope.of(scope)
        rows = (
            (
                await self.session.execute(
                    select(DomainPosture).where(
                        DomainPosture.project_id == project_id,
                        scope.match(DomainPosture.scan_id),
                    )
                )
            )
            .scalars()
            .all()
        )
        summary = _summarise(list(rows))
        ids = list(scope.ids)
        if len(ids) == 1:
            summary.scan_id = ids[0]
        if rows:
            summary.observed_at = max(r.discovered_at for r in rows)
        return summary

    async def for_target(
        self, project_id: UUID, target_id: UUID
    ) -> DomainPostureSummary:
        """The newest settled run of the target that checked its zones."""
        latest = (
            await self.session.execute(
                select(DomainPosture.scan_id, func.max(Scan.started_at).label("at"))
                .join(Scan, Scan.id == DomainPosture.scan_id)
                .where(
                    DomainPosture.project_id == project_id,
                    DomainPosture.target_id == target_id,
                    Scan.status.in_(SCAN_TERMINAL_STATUSES),
                    census_only(),
                )
                .group_by(DomainPosture.scan_id)
                .order_by(func.max(Scan.started_at).desc())
                .limit(1)
            )
        ).first()
        if latest is None:
            return DomainPostureSummary(target_id=target_id)
        summary = await self.summary(project_id, latest[0])
        summary.target_id = target_id
        summary.scan_id = latest[0]
        return summary

    async def _latest_scan_ids(self, project_id: UUID) -> list[UUID]:
        """Each target's newest settled census run that holds posture rows."""
        runs = (
            select(DomainPosture.scan_id, DomainPosture.target_id, Scan.started_at)
            .join(Scan, Scan.id == DomainPosture.scan_id)
            .where(
                DomainPosture.project_id == project_id,
                Scan.status.in_(SCAN_TERMINAL_STATUSES),
                census_only(),
            )
            .distinct()
            .subquery()
        )
        ranked = select(
            runs.c.scan_id,
            func.row_number()
            .over(partition_by=runs.c.target_id, order_by=runs.c.started_at.desc())
            .label("rank"),
        ).subquery()
        return list(
            (
                await self.session.execute(
                    select(ranked.c.scan_id).where(ranked.c.rank == 1)
                )
            )
            .scalars()
            .all()
        )

    async def for_project(self, project_id: UUID) -> DomainPostureSummary:
        """Every target's newest settled run, folded into one estate view."""
        scan_ids = await self._latest_scan_ids(project_id)
        if not scan_ids:
            return DomainPostureSummary()
        return await self.summary(project_id, QueryScope(tuple(scan_ids)))

    async def spoofable(
        self, project_id: UUID
    ) -> list[tuple[UUID, str, str, datetime]]:
        """(target_id, zone, failing check, observed_at) for zones open to forgery."""
        scan_ids = await self._latest_scan_ids(project_id)
        if not scan_ids:
            return []
        rows = (
            (
                await self.session.execute(
                    select(DomainPosture).where(
                        DomainPosture.project_id == project_id,
                        DomainPosture.scan_id.in_(scan_ids),
                        func.jsonb_exists_any(
                            cast(DomainPosture.posture_issues, JSONB),
                            pg_array(list(defs.SPOOFABLE_KEYS)),
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )
        out: list[tuple[UUID, str, str, datetime]] = []
        for zone in rows:
            hit = next(
                (k for k in defs.SPOOFABLE_KEYS if k in (zone.posture_issues or [])),
                None,
            )
            if hit is not None:
                out.append((zone.target_id, zone.zone, hit, zone.discovered_at))
        return out


__all__ = ["MAX_ZONES", "DomainPostureService"]
