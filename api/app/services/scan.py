import asyncio
import copy
import logging
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import Select, case, exists, func, nullslast, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services.proxy import ProxyService
from app.services.scan_context import ScanContextService
from app.services.scan_engine import ScanEngineService, stage_effects
from shared.config import BaseAppSettings
from shared.definitions.notifications import scan_cancelled
from shared.enums.api_key import APIProvider
from shared.enums.scan import SCAN_LIVE_STATUSES, ScanActivityStatus, ScanStatus
from shared.models.api_key import APIKey
from shared.models.scan import (
    SCAN_STATUSES,
    Scan,
    ScanBatchCreate,
    ScanChanges,
    ScanCreate,
    ScanDailyCount,
    ScanExportRow,
    ScanFacet,
    ScanRead,
    ScanStats,
    ScanStatusCounts,
)
from shared.models.scan_activity import ScanActivity, ScanActivityRead
from shared.models.scan_command import (
    ScanCommand,
    ScanCommandDetail,
    ScanCommandRead,
)
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import ScanEngine
from shared.models.scan_preview import (
    PreviewSummary,
    PreviewToolStatus,
    ScanPreview,
)
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.services.celery_dispatch import revoke_scan_tasks
from shared.services.notification import NotificationManager
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import (
    MASK,
    ResolvedScanConfig,
    _auth_summary,
    _check_baseline_deferred,
    mask_proxy_url,
    merge_engine_context,
    redact_command,
)
from shared.utils.datetime import utc_now

logger = logging.getLogger(__name__)

_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60

ScanSortKey = Literal["started", "duration", "status", "subdomains", "vulnerabilities"]
ScanSortDir = Literal["asc", "desc"]

_WINDOW_DELTAS = {
    "6h": timedelta(hours=6),
    "12h": timedelta(hours=12),
    "24h": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
}

MAX_SCAN_EXPORT = 50000

_STATUS_RANK = case(
    (Scan.status == ScanStatus.RUNNING.value, 0),
    (Scan.status == ScanStatus.PENDING.value, 1),
    (Scan.status == ScanStatus.COMPLETED.value, 2),
    (Scan.status == ScanStatus.FAILED.value, 3),
    else_=4,
)


def _mask_config_headers(config: dict) -> dict:
    out = copy.deepcopy(config)
    headers = out.get("headers") or {}
    out["headers"] = {
        name: (MASK if value else value) for name, value in headers.items()
    }
    if out.get("proxy_url"):
        out["proxy_url"] = mask_proxy_url(out["proxy_url"])
    if isinstance(out.get("tool_options"), dict):
        out["tool_options"] = {
            t: redact_command(v) for t, v in out["tool_options"].items()
        }

    return out


def _command_read(cmd: ScanCommand) -> ScanCommandRead:
    read = ScanCommandRead.model_validate(cmd, from_attributes=True)
    read.command = redact_command(read.command)
    return read


def _scan_duration(scan: Scan) -> float | None:
    if scan.started_at is None:
        return None
    end = scan.completed_at or (
        utc_now() if scan.status == ScanStatus.RUNNING.value else None
    )
    if end is None:
        return None
    return round((end - scan.started_at).total_seconds(), 1)


def _human_duration(seconds: int) -> str:
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s"
    minutes = seconds // _SECONDS_PER_MINUTE
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}m"
    hours = minutes // _MINUTES_PER_HOUR
    rem = minutes % _MINUTES_PER_HOUR
    return f"{hours}h {rem}m" if rem else f"{hours}h"


class ScanService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.engine_service = ScanEngineService(session)
        self.context_service = ScanContextService(session)

    async def _get_engine(self, engine_id: UUID, project_id: UUID) -> ScanEngine:
        result = await self.session.execute(
            select(ScanEngine).where(
                ScanEngine.id == engine_id, ScanEngine.project_id == project_id
            )
        )
        engine = result.scalar_one_or_none()
        if not engine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan engine not found"
            )
        return engine

    async def _get_context(self, context_id: UUID, project_id: UUID) -> ScanContext:
        result = await self.session.execute(
            select(ScanContext).where(
                ScanContext.id == context_id, ScanContext.project_id == project_id
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan context not found"
            )
        return ctx

    async def _get_targets(
        self, target_ids: list[UUID], project_id: UUID
    ) -> list[Target]:
        result = await self.session.execute(
            select(Target).where(
                Target.id.in_(target_ids), Target.project_id == project_id
            )
        )
        found = {t.id: t for t in result.scalars().all()}
        missing = [tid for tid in target_ids if tid not in found]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Target not found: {missing[0]}",
            )
        return [found[tid] for tid in target_ids]

    async def _get_target(self, target_id: UUID, project_id: UUID) -> Target:
        result = await self.session.execute(
            select(Target).where(
                Target.id == target_id, Target.project_id == project_id
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Target not found"
            )
        return target

    async def _resolve_scope(
        self, engine_id: UUID, context_id: UUID | None, project_id: UUID
    ):
        engine = await self._get_engine(engine_id, project_id)
        context = None
        if context_id is not None:
            context = await self._get_context(context_id, project_id)
            _check_baseline_deferred(
                context.compare_baseline_scan_id, context.scan_only_new_assets
            )

        proxy_url = None
        if context is not None and context.proxy_id is not None:
            proxy_url = await ProxyService(self.session).resolve_proxy_url(
                context.proxy_id
            )
        return engine, context, proxy_url

    async def _resolve_and_validate(self, data: ScanCreate, project_id: UUID):
        engine, context, proxy_url = await self._resolve_scope(
            data.engine_id, data.context_id, project_id
        )
        target = await self._get_target(data.target_id, project_id)
        resolved = merge_engine_context(
            engine,
            context,
            target.target_value,
            target.target_type.value,
            proxy_url=proxy_url,
        )
        return engine, context, target, resolved

    async def _configured_providers(self) -> set[str]:
        result = await self.session.execute(
            select(APIKey).where(APIKey.is_enabled == True)  # noqa: E712
        )
        configured = set()
        for key in result.scalars().all():
            provider = (
                key.provider.value
                if isinstance(key.provider, APIProvider)
                else key.provider
            )
            configured.add(provider)
        return configured

    async def preview(self, data: ScanCreate, project_id: UUID) -> ScanPreview:
        engine, context, target, resolved = await self._resolve_and_validate(
            data, project_id
        )
        configured = await self._configured_providers()

        phases, warnings = stage_effects(resolved, configured)

        will_run = sum(
            1 for p in phases for t in p.tools if t.status == PreviewToolStatus.WILL_RUN
        )
        est_seconds = will_run * _SECONDS_PER_MINUTE
        rates = resolved.per_tool_rate_limits
        rate_summary = ", ".join(f"{tool} {rates[tool]}/s" for tool in sorted(rates))
        if resolved.global_rate_limit_ceiling is not None:
            rate_summary += f" (ceiling {resolved.global_rate_limit_ceiling}/s)"

        auth = context.auth if context is not None else {"auth_type": "none"}
        extra_headers = context.extra_headers if context is not None else []
        custom_header_names = [
            h.get("name") for h in (extra_headers or []) if h.get("name")
        ]

        proxy_name = None
        if context is not None and context.proxy_id is not None:
            try:
                proxy_name = (
                    await ProxyService(self.session).get(context.proxy_id)
                ).name
            except HTTPException:
                proxy_name = None

        summary = PreviewSummary(
            auth_summary=_auth_summary(auth, extra_headers),
            custom_header_names=custom_header_names,
            rate_summary=rate_summary,
            thread_multiplier=resolved.thread_multiplier,
            timeout_multiplier=resolved.timeout_multiplier,
            http_protocol=resolved.http_protocol,
            follow_redirects=resolved.follow_redirects,
            excluded_subdomains_count=len(resolved.excluded_subdomains),
            excluded_paths_count=len(resolved.excluded_paths),
            excluded_ips_count=len(resolved.excluded_ips),
            excluded_subdomains=resolved.excluded_subdomains,
            excluded_paths=resolved.excluded_paths,
            excluded_ips=resolved.excluded_ips,
            included_subdomains=resolved.included_subdomains,
            proxy_name=proxy_name,
            estimated_duration_seconds=est_seconds,
            estimated_duration_human=_human_duration(est_seconds),
        )

        return ScanPreview(
            target_id=target.id,
            target_value=target.target_value,
            target_type=target.target_type.value,
            engine_id=engine.id,
            engine_name=engine.name,
            context_id=context.id if context is not None else None,
            context_name=context.name if context is not None else None,
            phases=phases,
            summary=summary,
            warnings=warnings,
        )

    async def create(
        self,
        data: ScanCreate,
        project_id: UUID,
        created_by: UUID,
        schedule_id: UUID | None = None,
        schedule_type: str | None = None,
    ) -> ScanRead:
        engine, context, target, resolved = await self._resolve_and_validate(
            data, project_id
        )
        logger.info(
            "Creating scan for target=%s engine=%s header_names=%s",
            target.id,
            engine.id,
            list(resolved.headers.keys()),
        )

        scan = build_scan_row(
            resolved=resolved,
            engine=engine,
            context=context,
            target=target,
            project_id=project_id,
            created_by=created_by,
            schedule_id=schedule_id,
            schedule_type=schedule_type,
        )
        self.session.add(scan)
        await self.session.commit()
        await self.session.refresh(scan)

        await self.engine_service.touch(engine.id, project_id)
        if context is not None:
            await self.context_service.touch(context.id, project_id, scan_id=scan.id)

        self._dispatch_scan(scan)
        return self._to_read(scan)

    async def create_batch(
        self,
        data: ScanBatchCreate,
        project_id: UUID,
        created_by: UUID,
    ) -> list[ScanRead]:
        engine, context, proxy_url = await self._resolve_scope(
            data.engine_id, data.context_id, project_id
        )
        target_ids = list(dict.fromkeys(data.target_ids))
        targets = await self._get_targets(target_ids, project_id)

        scans: list[Scan] = []
        for target in targets:
            resolved = merge_engine_context(
                engine,
                context,
                target.target_value,
                target.target_type.value,
                proxy_url=proxy_url,
            )
            scan = build_scan_row(
                resolved=resolved,
                engine=engine,
                context=context,
                target=target,
                project_id=project_id,
                created_by=created_by,
            )
            self.session.add(scan)
            scans.append(scan)

        logger.info("Creating %d scans for engine=%s", len(scans), engine.id)
        await self.session.commit()

        await self.engine_service.touch(engine.id, project_id)
        if context is not None:
            await self.context_service.touch(
                context.id, project_id, scan_id=scans[-1].id
            )

        await self._dispatch_batch(scans)
        return [self._to_read(scan) for scan in scans]

    def _dispatch_scan(self, scan: Scan) -> None:
        from shared.services.celery_dispatch import dispatch_scan_run  # noqa: PLC0415

        dispatch_scan_run(str(scan.id))

    def _dispatch_each(self, scans: list[Scan]) -> list[Scan]:
        failed = []
        for scan in scans:
            try:
                self._dispatch_scan(scan)
            except Exception:
                logger.exception("Failed to dispatch scan %s", scan.id)
                failed.append(scan)
        return failed

    async def _dispatch_batch(self, scans: list[Scan]) -> None:
        failed = await asyncio.to_thread(self._dispatch_each, scans)
        if not failed:
            return
        for scan in failed:
            scan.status = ScanStatus.FAILED.value
            scan.error = "Could not be queued for execution."
            scan.completed_at = utc_now()
        await self.session.commit()

    def _sort_expr(self, sort_by: ScanSortKey):
        if sort_by == "duration":
            return func.extract(
                "epoch", func.coalesce(Scan.completed_at, utc_now()) - Scan.started_at
            )
        if sort_by == "status":
            return _STATUS_RANK
        if sort_by == "subdomains":
            return Scan.subdomains_found
        if sort_by == "vulnerabilities":
            return Scan.vulnerabilities_found
        return func.coalesce(Scan.started_at, Scan.created_at)

    def _filter_conditions(
        self,
        m,
        statuses: list[str] | None,
        engines: list[str] | None,
        contexts: list[str] | None,
        time_range: str | None,
    ) -> list:
        conds: list = []
        if statuses:
            conds.append(m.status.in_(statuses))
        if engines:
            conds.append(m.engine_name.in_(engines))
        if contexts:
            conds.append(m.context_name.in_(contexts))
        if time_range and time_range in _WINDOW_DELTAS:
            cutoff = utc_now() - _WINDOW_DELTAS[time_range]
            conds.append(func.coalesce(m.started_at, m.created_at) >= cutoff)
        return conds

    def build_list_query(
        self,
        project_id: UUID,
        target_id: UUID | None = None,
        statuses: list[str] | None = None,
        engines: list[str] | None = None,
        contexts: list[str] | None = None,
        search: str | None = None,
        time_range: str | None = None,
        sort_by: ScanSortKey = "started",
        sort_dir: ScanSortDir = "desc",
        schedule_id: UUID | None = None,
        scheduled: bool | None = None,
    ) -> Select:
        query = select(Scan).where(
            Scan.project_id == project_id,
            *self._filter_conditions(Scan, statuses, engines, contexts, time_range),
        )
        if target_id is not None:
            query = query.where(Scan.target_id == target_id)
        if schedule_id is not None:
            query = query.where(Scan.schedule_id == schedule_id)
        if scheduled is True:
            query = query.where(Scan.schedule_type.is_not(None))
        elif scheduled is False:
            query = query.where(Scan.schedule_type.is_(None))
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.join(Target, Scan.target_id == Target.id).where(
                or_(
                    func.lower(Target.target_value).like(term),
                    func.lower(Scan.engine_name).like(term),
                    func.lower(func.coalesce(Scan.context_name, "")).like(term),
                )
            )

        expr = self._sort_expr(sort_by)
        ordering = expr.asc() if sort_dir == "asc" else expr.desc()
        # Only `duration` can be NULL (un-started scans); nulls-last on the others
        # would break the ix_scans_*_started index match (default DESC is nulls-first).
        if sort_by == "duration":
            ordering = nullslast(ordering)
        return query.order_by(ordering, Scan.created_at.desc())

    def build_target_groups_query(
        self,
        project_id: UUID,
        statuses: list[str] | None = None,
        engines: list[str] | None = None,
        contexts: list[str] | None = None,
        search: str | None = None,
        time_range: str | None = None,
    ) -> Select:
        last_t = func.coalesce(Scan.started_at, Scan.created_at)
        inner = aliased(Scan)
        last_status = (
            select(inner.status)
            .where(
                inner.target_id == Scan.target_id,
                inner.project_id == project_id,
                *self._filter_conditions(
                    inner, statuses, engines, contexts, time_range
                ),
            )
            .order_by(func.coalesce(inner.started_at, inner.created_at).desc())
            .limit(1)
            .correlate(Scan)
            .scalar_subquery()
        )
        live = case(
            (
                Scan.status.in_([ScanStatus.RUNNING.value, ScanStatus.PENDING.value]),
                1,
            ),
            else_=0,
        )
        query = (
            select(
                Scan.target_id.label("target_id"),
                Target.target_value.label("target_value"),
                Target.target_type.label("target_type"),
                func.count().label("scan_count"),
                func.max(last_t).label("last_scan_at"),
                func.sum(live).label("running"),
                last_status.label("last_status"),
            )
            .join(Target, Scan.target_id == Target.id)
            .where(
                Scan.project_id == project_id,
                *self._filter_conditions(Scan, statuses, engines, contexts, time_range),
            )
            .group_by(Scan.target_id, Target.target_value, Target.target_type)
        )
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Target.target_value).like(term),
                    func.lower(Scan.engine_name).like(term),
                    func.lower(func.coalesce(Scan.context_name, "")).like(term),
                )
            )
        return query.order_by(func.max(last_t).desc())

    def to_read(self, scan: Scan) -> ScanRead:
        return self._to_read(scan)

    async def export_rows(
        self,
        project_id: UUID,
        target_id: UUID | None = None,
        statuses: list[str] | None = None,
        engines: list[str] | None = None,
        contexts: list[str] | None = None,
        search: str | None = None,
        time_range: str | None = None,
        sort_by: ScanSortKey = "started",
        sort_dir: ScanSortDir = "desc",
        scheduled: bool | None = None,
    ) -> list[ScanExportRow]:
        query = self.build_list_query(
            project_id=project_id,
            target_id=target_id,
            statuses=statuses,
            engines=engines,
            contexts=contexts,
            search=search,
            time_range=time_range,
            sort_by=sort_by,
            sort_dir=sort_dir,
            scheduled=scheduled,
        ).limit(MAX_SCAN_EXPORT)
        result = await self.session.execute(query)
        return [
            ScanExportRow(
                target=(scan.execution_config or {}).get("target_value", ""),
                status=scan.status,
                engine=scan.engine_name,
                context=scan.context_name,
                schedule_type=scan.schedule_type,
                subdomains=scan.subdomains_found,
                ips=scan.ips_found,
                open_ports=scan.open_ports_found,
                vulnerabilities=scan.vulnerabilities_found,
                endpoints=scan.endpoints_found,
                duration_seconds=_scan_duration(scan),
                started_at=scan.started_at,
                completed_at=scan.completed_at,
                created_at=scan.created_at,
            )
            for scan in result.scalars().all()
        ]

    async def new_subdomain_counts(
        self, scan_ids: list[UUID], target_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Per scan, how many subdomain names it was the FIRST to discover for its target."""
        if not scan_ids or not target_ids:
            return {}
        rn = (
            func.row_number()
            .over(
                partition_by=[Subdomain.target_id, Subdomain.name],
                order_by=[Subdomain.discovered_at.asc(), Subdomain.scan_id.asc()],
            )
            .label("rn")
        )
        firsts = (
            select(Subdomain.scan_id.label("scan_id"), rn)
            .where(Subdomain.target_id.in_(target_ids))
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(firsts.c.scan_id, func.count())
                .where(firsts.c.rn == 1, firsts.c.scan_id.in_(scan_ids))
                .group_by(firsts.c.scan_id)
            )
        ).all()
        return dict(rows)

    async def prev_completed_counts(
        self, scan_ids: list[UUID], target_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Per scan, the previous COMPLETED scan's subdomains_found for the same target."""
        if not scan_ids or not target_ids:
            return {}
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        prev = (
            func.lag(Scan.subdomains_found)
            .over(partition_by=Scan.target_id, order_by=ordering.asc())
            .label("prev")
        )
        completed = (
            select(Scan.id.label("id"), prev)
            .where(
                Scan.target_id.in_(target_ids),
                Scan.status == ScanStatus.COMPLETED.value,
            )
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(completed.c.id, completed.c.prev).where(
                    completed.c.id.in_(scan_ids)
                )
            )
        ).all()
        return {sid: p for sid, p in rows if p is not None}

    async def first_scan_ids(self, target_ids: list[UUID]) -> set[UUID]:
        """The earliest scan id for each target (baseline run — no prior to diff against)."""
        if not target_ids:
            return set()
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        rn = (
            func.row_number()
            .over(
                partition_by=Scan.target_id,
                order_by=[ordering.asc(), Scan.created_at.asc()],
            )
            .label("rn")
        )
        sub = (
            select(Scan.id.label("id"), rn)
            .where(Scan.target_id.in_(target_ids))
            .subquery()
        )
        rows = (await self.session.execute(select(sub.c.id).where(sub.c.rn == 1))).all()
        return {r[0] for r in rows}

    async def gone_subdomain_counts(
        self, scan_ids: list[UUID], target_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Per scan, subdomain names present in the previous completed run but absent now."""
        if not scan_ids or not target_ids:
            return {}
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        prev_id = (
            func.lag(Scan.id)
            .over(partition_by=Scan.target_id, order_by=ordering.asc())
            .label("prev_id")
        )
        completed = (
            select(Scan.id.label("id"), prev_id)
            .where(
                Scan.target_id.in_(target_ids),
                Scan.status == ScanStatus.COMPLETED.value,
            )
            .subquery()
        )
        pairs = (
            select(completed.c.id, completed.c.prev_id)
            .where(completed.c.id.in_(scan_ids), completed.c.prev_id.is_not(None))
            .subquery()
        )
        sp = aliased(Subdomain)
        sc = aliased(Subdomain)
        query = (
            select(pairs.c.id, func.count())
            .select_from(pairs)
            .join(sp, sp.scan_id == pairs.c.prev_id)
            .where(
                ~exists(select(1).where(sc.scan_id == pairs.c.id, sc.name == sp.name))
            )
            .group_by(pairs.c.id)
        )
        rows = (await self.session.execute(query)).all()
        return dict(rows)

    async def target_trends(
        self, target_ids: list[UUID], limit: int = 12
    ) -> dict[UUID, list[int]]:
        """Per target, subdomains_found across its completed runs (oldest→newest, last `limit`)."""
        if not target_ids:
            return {}
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        rows = (
            await self.session.execute(
                select(Scan.target_id, Scan.subdomains_found)
                .where(
                    Scan.target_id.in_(target_ids),
                    Scan.status == ScanStatus.COMPLETED.value,
                )
                .order_by(Scan.target_id, ordering.asc())
            )
        ).all()
        out: dict[UUID, list[int]] = {}
        for tid, n in rows:
            out.setdefault(tid, []).append(n)
        return {tid: vals[-limit:] for tid, vals in out.items()}

    async def retired_subdomain_total(
        self, project_id: UUID, cutoff: datetime, target_id: UUID | None = None
    ) -> int:
        """Subdomains dropped by each target's latest completed scan that ran in the window."""
        ordering = func.coalesce(Scan.started_at, Scan.created_at)
        rn = (
            func.row_number()
            .over(partition_by=Scan.target_id, order_by=ordering.desc())
            .label("rn")
        )
        conds = [
            Scan.project_id == project_id,
            Scan.status == ScanStatus.COMPLETED.value,
        ]
        if target_id is not None:
            conds.append(Scan.target_id == target_id)
        latest = (
            select(
                Scan.id.label("id"),
                Scan.target_id.label("tid"),
                ordering.label("t"),
                rn,
            )
            .where(*conds)
            .subquery()
        )
        rows = (
            await self.session.execute(
                select(latest.c.id, latest.c.tid).where(
                    latest.c.rn == 1, latest.c.t >= cutoff
                )
            )
        ).all()
        if not rows:
            return 0
        scan_ids = [r[0] for r in rows]
        target_ids = list({r[1] for r in rows})
        gone = await self.gone_subdomain_counts(scan_ids, target_ids)
        return sum(gone.values())

    async def changes(
        self, project_id: UUID, window: str, target_id: UUID | None = None
    ) -> ScanChanges:
        cutoff = utc_now() - _WINDOW_DELTAS.get(window, timedelta(days=7))

        sub_conds = [Subdomain.project_id == project_id]
        if target_id is not None:
            sub_conds.append(Subdomain.target_id == target_id)
        firsts = (
            select(
                Subdomain.target_id.label("target_id"),
                func.min(Subdomain.discovered_at).label("first_seen"),
            )
            .where(*sub_conds)
            .group_by(Subdomain.target_id, Subdomain.name)
            .subquery()
        )
        new_subdomains = (
            await self.session.execute(
                select(func.count()).where(firsts.c.first_seen >= cutoff)
            )
        ).scalar_one()
        targets_changed = (
            await self.session.execute(
                select(func.count(func.distinct(firsts.c.target_id))).where(
                    firsts.c.first_seen >= cutoff
                )
            )
        ).scalar_one()

        scan_conds = [Scan.project_id == project_id, Scan.created_at >= cutoff]
        if target_id is not None:
            scan_conds.append(Scan.target_id == target_id)
        scans_run = (
            await self.session.execute(select(func.count()).where(*scan_conds))
        ).scalar_one()
        failed_runs = (
            await self.session.execute(
                select(func.count()).where(
                    *scan_conds,
                    Scan.status.in_(
                        [ScanStatus.FAILED.value, ScanStatus.CANCELLED.value]
                    ),
                )
            )
        ).scalar_one()

        retired = await self.retired_subdomain_total(project_id, cutoff, target_id)

        return ScanChanges(
            window=window,
            new_subdomains=new_subdomains,
            retired_subdomains=retired,
            targets_changed=targets_changed,
            scans_run=scans_run,
            failed_runs=failed_runs,
        )

    async def stats(self, project_id: UUID, target_id: UUID | None = None) -> ScanStats:
        conds = [Scan.project_id == project_id]
        if target_id is not None:
            conds.append(Scan.target_id == target_id)

        status_rows = (
            await self.session.execute(
                select(Scan.status, func.count()).where(*conds).group_by(Scan.status)
            )
        ).all()
        counts = dict.fromkeys(SCAN_STATUSES, 0)
        total = 0
        for st, n in status_rows:
            if st in counts:
                counts[st] = n
            total += n

        last_scan_at = (
            await self.session.execute(select(func.max(Scan.created_at)).where(*conds))
        ).scalar_one_or_none()

        avg_duration = (
            await self.session.execute(
                select(
                    func.avg(func.extract("epoch", Scan.completed_at - Scan.started_at))
                ).where(
                    *conds,
                    Scan.status == ScanStatus.COMPLETED.value,
                    Scan.started_at.is_not(None),
                    Scan.completed_at.is_not(None),
                )
            )
        ).scalar_one_or_none()

        finished = (
            counts[ScanStatus.COMPLETED.value]
            + counts[ScanStatus.FAILED.value]
            + counts[ScanStatus.CANCELLED.value]
        )
        success_rate = (
            counts[ScanStatus.COMPLETED.value] / finished if finished else None
        )

        start = (utc_now() - timedelta(days=29)).date()
        status_day_rows = (
            await self.session.execute(
                select(func.date(Scan.created_at), Scan.status, func.count())
                .where(*conds, func.date(Scan.created_at) >= start)
                .group_by(func.date(Scan.created_at), Scan.status)
            )
        ).all()

        by_day_status: dict[str, dict[str, int]] = {}
        for d, st, n in status_day_rows:
            by_day_status.setdefault(str(d), {})[st] = n

        sub_conds = [Subdomain.project_id == project_id]
        if target_id is not None:
            sub_conds.append(Subdomain.target_id == target_id)
        firsts = (
            select(func.min(Subdomain.discovered_at).label("first_seen"))
            .where(*sub_conds)
            .group_by(Subdomain.target_id, Subdomain.name)
            .subquery()
        )
        first_day = func.date(firsts.c.first_seen)
        new_day_rows = (
            await self.session.execute(
                select(first_day, func.count())
                .where(first_day >= start)
                .group_by(first_day)
            )
        ).all()
        new_by_day = {str(d): n for d, n in new_day_rows}

        daily = []
        for i in range(30):
            d = (start + timedelta(days=i)).isoformat()
            s = by_day_status.get(d, {})
            daily.append(
                ScanDailyCount(
                    date=d,
                    count=sum(s.values()),
                    completed=s.get(ScanStatus.COMPLETED.value, 0),
                    failed=s.get(ScanStatus.FAILED.value, 0),
                    cancelled=s.get(ScanStatus.CANCELLED.value, 0),
                    running=s.get(ScanStatus.RUNNING.value, 0),
                    pending=s.get(ScanStatus.PENDING.value, 0),
                    new_subdomains=new_by_day.get(d, 0),
                )
            )

        engine_rows = (
            await self.session.execute(
                select(Scan.engine_name, func.count())
                .where(*conds)
                .group_by(Scan.engine_name)
                .order_by(func.count().desc())
            )
        ).all()
        engines = [ScanFacet(name=name, count=n) for name, n in engine_rows if name]

        context_rows = (
            await self.session.execute(
                select(Scan.context_name, func.count())
                .where(*conds, Scan.context_name.is_not(None))
                .group_by(Scan.context_name)
                .order_by(func.count().desc())
            )
        ).all()
        contexts = [ScanFacet(name=name, count=n) for name, n in context_rows if name]

        return ScanStats(
            total=total,
            running=counts[ScanStatus.RUNNING.value],
            by_status=ScanStatusCounts(**counts),
            last_scan_at=last_scan_at,
            avg_duration_seconds=(
                round(avg_duration, 1) if avg_duration is not None else None
            ),
            success_rate=round(success_rate, 3) if success_rate is not None else None,
            daily=daily,
            engines=engines,
            contexts=contexts,
        )

    async def get(self, id: UUID, project_id: UUID) -> ScanRead:
        scan = await self._get_scan(id, project_id)
        read = self._to_read(scan)
        await self.attach_deltas([read])
        return read

    async def attach_deltas(self, items: list[ScanRead]) -> None:
        if not items:
            return
        scan_ids = [i.id for i in items]
        target_ids = list({i.target_id for i in items})
        new_counts = await self.new_subdomain_counts(scan_ids, target_ids)
        gone_counts = await self.gone_subdomain_counts(scan_ids, target_ids)
        prev_counts = await self.prev_completed_counts(scan_ids, target_ids)
        first_ids = await self.first_scan_ids(target_ids)
        for i in items:
            i.new_subdomains = new_counts.get(i.id, 0)
            i.gone_subdomains = gone_counts.get(i.id, 0)
            i.prev_subdomains_found = prev_counts.get(i.id)
            i.is_first_scan = i.id in first_ids

    async def _get_scan(self, id: UUID, project_id: UUID) -> Scan:
        result = await self.session.execute(
            select(Scan).where(Scan.id == id, Scan.project_id == project_id)
        )
        scan = result.scalar_one_or_none()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
            )
        return scan

    async def cancel(self, id: UUID, project_id: UUID) -> ScanRead:
        scan = await self._get_scan(id, project_id)
        if scan.status in SCAN_LIVE_STATUSES:
            scan.status = ScanStatus.CANCELLED.value
            scan.completed_at = utc_now()
            scan.error = "Cancelled by user."
            await self.session.commit()

            revoke_scan_tasks(scan.celery_task_ids or [])
            now = utc_now()
            for model in (ScanActivity, ScanCommand):
                await self.session.execute(
                    update(model)
                    .where(
                        model.scan_id == scan.id,
                        model.status == ScanActivityStatus.RUNNING.value,
                    )
                    .values(status=ScanActivityStatus.ABORTED.value, completed_at=now)
                )
            await self.session.commit()
            await self._announce_cancelled(scan)
            await self.session.refresh(scan)
        return self._to_read(scan)

    async def _announce_cancelled(self, scan: Scan) -> None:
        target_value = (scan.execution_config or {}).get("target_value", "")
        payload = scan_cancelled(str(scan.id), target_value, scan.engine_name)
        try:
            await NotificationManager.publish(
                session=self.session,
                type=payload["type"],
                severity=payload["severity"],
                title=payload["title"],
                message=payload["message"],
                metadata=payload.get("metadata"),
            )
        except Exception:
            logger.warning("cancel notification dispatch failed", exc_info=True)
        try:
            ScanEventPublisher(
                BaseAppSettings().redis_url,
                scan_id=str(scan.id),
                project_id=str(scan.project_id),
            ).scan_cancelled(status=ScanStatus.CANCELLED.value)
        except Exception:
            logger.debug("cancel event emit failed", exc_info=True)

    async def list_activities(
        self, scan_id: UUID, project_id: UUID
    ) -> list[ScanActivityRead]:
        await self._get_scan(scan_id, project_id)
        rows = (
            (
                await self.session.execute(
                    select(ScanActivity)
                    .where(ScanActivity.scan_id == scan_id)
                    .order_by(ScanActivity.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        counts = dict(
            (
                await self.session.execute(
                    select(ScanCommand.activity_id, func.count())
                    .where(ScanCommand.scan_id == scan_id)
                    .group_by(ScanCommand.activity_id)
                )
            ).all()
        )
        out: list[ScanActivityRead] = []
        for a in rows:
            read = ScanActivityRead.model_validate(a, from_attributes=True)
            read.command_count = counts.get(a.id, 0)
            read.duration_seconds = (
                round((a.completed_at - a.started_at).total_seconds(), 1)
                if a.started_at and a.completed_at
                else None
            )
            out.append(read)
        return out

    async def list_commands(
        self,
        scan_id: UUID,
        project_id: UUID,
        activity_id: UUID | None = None,
    ) -> list[ScanCommandRead]:
        await self._get_scan(scan_id, project_id)
        query = select(ScanCommand).where(ScanCommand.scan_id == scan_id)
        if activity_id is not None:
            query = query.where(ScanCommand.activity_id == activity_id)
        rows = (
            (await self.session.execute(query.order_by(ScanCommand.started_at.asc())))
            .scalars()
            .all()
        )
        return [_command_read(c) for c in rows]

    async def get_command(
        self, scan_id: UUID, command_id: UUID, project_id: UUID
    ) -> ScanCommandDetail:
        await self._get_scan(scan_id, project_id)
        cmd = (
            await self.session.execute(
                select(ScanCommand).where(
                    ScanCommand.id == command_id, ScanCommand.scan_id == scan_id
                )
            )
        ).scalar_one_or_none()
        if cmd is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Command not found"
            )
        detail = ScanCommandDetail.model_validate(cmd, from_attributes=True)
        detail.command = redact_command(detail.command)
        if detail.output:
            detail.output = redact_command(detail.output)
        return detail

    async def delete(self, id: UUID, project_id: UUID) -> None:
        scan = await self._get_scan(id, project_id)
        if scan.status in SCAN_LIVE_STATUSES:
            revoke_scan_tasks(scan.celery_task_ids or [])
        await self.session.delete(scan)
        await self.session.commit()

    def _to_read(self, scan: Scan) -> ScanRead:
        cfg = copy.deepcopy(scan.execution_config or {})
        cfg.pop("_auth_header_names", None)
        auth = cfg.pop("_auth", None) or {"auth_type": "none"}
        masked = _mask_config_headers(cfg)
        resolved = ResolvedScanConfig(**masked)
        return ScanRead(
            id=scan.id,
            project_id=scan.project_id,
            target_id=scan.target_id,
            engine_id=scan.engine_id,
            engine_name=scan.engine_name,
            context_id=scan.context_id,
            context_name=scan.context_name,
            schedule_id=scan.schedule_id,
            schedule_type=scan.schedule_type,
            execution_config=resolved,
            auth_summary=_auth_summary(auth, list(masked.get("headers", {}).keys())),
            status=scan.status,
            subdomains_found=scan.subdomains_found,
            ips_found=scan.ips_found,
            open_ports_found=scan.open_ports_found,
            http_assets_found=scan.http_assets_found,
            vulnerabilities_found=scan.vulnerabilities_found,
            endpoints_found=scan.endpoints_found,
            error=scan.error,
            created_by=scan.created_by,
            created_at=scan.created_at,
            started_at=scan.started_at,
            completed_at=scan.completed_at,
            duration_seconds=_scan_duration(scan),
        )
