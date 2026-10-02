import asyncio
import copy
import logging
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import (
    Select,
    and_,
    case,
    cast,
    column,
    exists,
    func,
    not_,
    nullslast,
    or_,
    select,
    true,
    tuple_,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.services import scan_deltas as stored_deltas
from app.services.proxy import ProxyService
from app.services.scan_context import ScanContextService
from app.services.scan_engine import ScanEngineService, stage_effects
from app.services.target import TargetService
from shared.definitions.compare import Tone
from shared.definitions.rescan import change_dimension, rescan_label
from shared.definitions.surface import SurfaceDimension
from shared.definitions.vulnerabilities import ACTIONABLE_SEVERITIES, Severity
from shared.definitions.watch import WATCH_HOST_KEY
from shared.enums.activity import ActivityEvent, ActivityLevel
from shared.enums.api_key import APIProvider
from shared.enums.scan import (
    SCAN_LIVE_STATUSES,
    SCAN_OPEN_STATUSES,
    ScanActivityStatus,
    ScanScope,
    ScanStatus,
)
from shared.enums.scan_context import AuthType
from shared.models.api_key import APIKey
from shared.models.instance_settings import SINGLETON_KEY, InstanceSettings
from shared.models.recheck import AssetRecheck
from shared.models.scan import (
    SCAN_STATUSES,
    RecheckFieldCount,
    RecheckTally,
    RescanSummary,
    Scan,
    ScanBatchCreate,
    ScanCancelAll,
    ScanCreate,
    ScanDaily,
    ScanDay,
    ScanFacet,
    ScanFindings,
    ScanRead,
    ScanStats,
    ScanStatusCounts,
    ScanTargetTrend,
    ScanTrendPoint,
    fold_pause,
    run_seconds,
)
from shared.models.scan_activity import ScanActivity, ScanActivityRead
from shared.models.scan_command import (
    ScanCommand,
    ScanCommandDetail,
    ScanCommandRead,
)
from shared.models.scan_context import ScanContext
from shared.models.scan_delta import ScanDelta
from shared.models.scan_engine import ScanEngine
from shared.models.scan_preview import (
    PreviewSummary,
    PreviewToolStatus,
    ScanPreview,
)
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability
from shared.services import scan_admission, scan_deltas, target_seeds
from shared.services.activity_log import ActivityLogService
from shared.services.asset_query import QueryScope, vuln_suppressed
from shared.services.celery_dispatch import (
    dispatch_scan_admission,
    dispatch_scan_finalize,
    dispatch_scan_resume,
    dispatch_scan_run,
    revoke_scan_tasks,
)
from shared.services.launch_plan import AdHocEngine, plan_label
from shared.services.orchestrator.events import ScanEventPublisher
from shared.services.scan_factory import build_scan_row
from shared.services.scan_resolve import (
    MASK,
    ResolvedScanConfig,
    _auth_summary,
    is_sealed,
    mask_proxy_url,
    merge_engine_context,
    redact_command,
)
from shared.services.scan_scope import census_only, covering_stages, covers
from shared.utils.datetime import duration_text, utc_now
from shared.utils.validation import unrecognised_target, validate_target
from stages.registry import resume_point

logger = logging.getLogger(__name__)

_SECONDS_PER_MINUTE = 60

ScanSortKey = Literal["started", "duration", "status", "subdomains", "vulnerabilities"]
ScanSortDir = Literal["asc", "desc"]

_RAN = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)
_SHORT = (ScanActivityStatus.PARTIAL.value, ScanActivityStatus.FAILED.value)
TREND_POINTS = 10
MAX_TREND_TARGETS = 100
MAX_DAILY_WINDOW = 90

_FINDINGS_RANK = (
    select(
        func.coalesce(
            func.sum(
                case(
                    (Vulnerability.severity == Severity.CRITICAL.value, 1_000_000),
                    (Vulnerability.severity == Severity.HIGH.value, 1_000),
                    else_=1,
                )
            ),
            0,
        )
    )
    .where(
        Vulnerability.scan_id == Scan.id,
        Vulnerability.severity.in_(ACTIONABLE_SEVERITIES),
    )
    .correlate(Scan)
    .scalar_subquery()
)

_STATUS_RANK = case(
    (Scan.status == ScanStatus.RUNNING.value, 0),
    (Scan.status == ScanStatus.PENDING.value, 1),
    (Scan.status == ScanStatus.COMPLETED.value, 2),
    (Scan.status == ScanStatus.FAILED.value, 3),
    else_=4,
)


def _resolved_config(scan_id: UUID, masked: dict) -> ResolvedScanConfig:
    try:
        return ResolvedScanConfig(**masked)
    except ValidationError as exc:
        bad = {str(e["loc"][0]) for e in exc.errors() if e["loc"]}
        logger.warning("scan %s has an unusable execution_config: %s", scan_id, bad)
        safe = {"target_value": "", "target_type": ""}
        safe.update({k: v for k, v in masked.items() if k not in bad})
        return ResolvedScanConfig(**safe)


def _mask_config_headers(config: dict) -> dict:
    out = copy.deepcopy(config)
    headers = out.get("headers") or {}
    out["headers"] = {
        name: (MASK if value else value) for name, value in headers.items()
    }
    proxy = out.get("proxy_url")
    if proxy:
        out["proxy_url"] = MASK if is_sealed(proxy) else mask_proxy_url(proxy)
    if isinstance(out.get("tool_options"), dict):
        out["tool_options"] = {
            t: MASK if is_sealed(v) else redact_command(v)
            for t, v in out["tool_options"].items()
        }

    return out


def _command_read(cmd: ScanCommand) -> ScanCommandRead:
    read = ScanCommandRead.model_validate(cmd, from_attributes=True)
    read.command = redact_command(read.command)
    return read


_UNSETTLED_ACTIVITY_STATUSES = (
    ScanActivityStatus.RUNNING.value,
    ScanActivityStatus.PAUSED.value,
)


def scan_duration(scan: Scan) -> float | None:
    if scan.started_at is None:
        return None
    ran = run_seconds(scan, scan.completed_at or _open_end(scan))
    return None if ran is None else round(ran, 1)


def _open_end(scan: Scan) -> datetime | None:
    if scan.status == ScanStatus.RUNNING.value:
        return utc_now()
    return scan.paused_at if scan.status == ScanStatus.PAUSED.value else None


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
        self, engine_id: UUID | None, context_id: UUID | None, project_id: UUID
    ):
        engine = (
            await self._get_engine(engine_id, project_id)
            if engine_id is not None
            else AdHocEngine()
        )
        context = None
        if context_id is not None:
            context = await self._get_context(context_id, project_id)

        proxy_url = await ProxyService(self.session).scan_proxy_url(context)
        return engine, context, proxy_url

    @staticmethod
    def _resolve_for(
        engine,
        context,
        target: Target,
        proxy_url: str | None,
        data: ScanCreate | ScanBatchCreate,
        stored_seeds: list[dict] | None = None,
    ):
        resolved = merge_engine_context(
            engine,
            context,
            target.target_value,
            target.target_type.value,
            proxy_url=proxy_url,
            overrides=data.overrides,
            intensity=data.intensity,
        )
        seeds = list(getattr(data, "seed_assets", None) or [])
        if seeds:
            target_seeds.apply(
                resolved, [seed.model_dump() for seed in seeds], seed_only=True
            )
        elif target.seed_scans:
            target_seeds.apply(resolved, stored_seeds or [], seed_only=False)
        if engine.id is None:
            label = (
                rescan_label(data.dimension or "", len(seeds))
                if seeds
                else plan_label(resolved)
            )
            engine = replace(engine, name=label)
        return engine, resolved

    async def _launch_target(
        self, data: ScanCreate, project_id: UUID, created_by: UUID | None
    ) -> Target:
        """The saved target, created from `target_value` when launching."""
        if data.target_id is not None:
            return await self._get_target(data.target_id, project_id)
        value = (data.target_value or "").strip()
        if created_by is not None:
            ensured = await TargetService(self.session).ensure_targets(
                [value], project_id, created_by
            )
            return ensured[0]
        target_type = validate_target(value)
        if target_type is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=unrecognised_target(value),
            )
        return Target(
            target_value=value, target_type=target_type, project_id=project_id
        )

    async def _resolve_and_validate(
        self, data: ScanCreate, project_id: UUID, created_by: UUID | None = None
    ):
        engine, context, proxy_url = await self._resolve_scope(
            data.engine_id, data.context_id, project_id
        )
        target = await self._launch_target(data, project_id, created_by)
        stored = await target_seeds.load_async(self.session, [target.id])
        engine, resolved = self._resolve_for(
            engine, context, target, proxy_url, data, stored.get(target.id)
        )
        return engine, context, target, resolved

    async def _batch_targets(
        self, data: ScanBatchCreate, project_id: UUID, created_by: UUID
    ) -> list[Target]:
        targets: list[Target] = []
        if data.target_ids:
            targets = await self._get_targets(
                list(dict.fromkeys(data.target_ids)), project_id
            )
        if data.target_values:
            seen = {t.id for t in targets}
            ensured = await TargetService(self.session).ensure_targets(
                data.target_values, project_id, created_by
            )
            targets.extend(t for t in ensured if t.id not in seen)
        return targets

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

    async def _live_runs(self, target_id: UUID | None, project_id: UUID) -> int:
        """Runs already sending traffic to this target."""
        if target_id is None:
            return 0
        return (
            await self.session.scalar(
                select(func.count())
                .select_from(Scan)
                .where(
                    Scan.target_id == target_id,
                    Scan.project_id == project_id,
                    Scan.status.in_(SCAN_LIVE_STATUSES),
                )
            )
        ) or 0

    async def preview(self, data: ScanCreate, project_id: UUID) -> ScanPreview:
        engine, context, target, resolved = await self._resolve_and_validate(
            data, project_id
        )
        configured = await self._configured_providers()

        phases, warnings = stage_effects(resolved, configured)
        live = await self._live_runs(target.id, project_id)
        if live:
            warnings.append(
                f"{live} run{'' if live == 1 else 's'} in progress on "
                f"{target.target_value}."
            )

        will_run = sum(
            1 for p in phases for t in p.tools if t.status == PreviewToolStatus.WILL_RUN
        )
        est_seconds = will_run * _SECONDS_PER_MINUTE
        to_target = sum(
            t.rate or 0
            for p in phases
            for t in p.tools
            if t.status == PreviewToolStatus.WILL_RUN
        )
        rate_summary = f"~{to_target}/s to target" if to_target else "no target traffic"
        if resolved.global_rate_limit_ceiling is not None:
            rate_summary += f", ceiling {resolved.global_rate_limit_ceiling}/s per tool"

        auth = (
            context.auth if context is not None else {"auth_type": AuthType.NONE.value}
        )
        extra_headers = context.extra_headers if context is not None else []
        custom_header_names = [
            h.get("name") for h in (extra_headers or []) if h.get("name")
        ]

        proxy = await ProxyService(self.session).scan_proxy(context)
        proxy_name = proxy.name if proxy is not None and proxy.is_active else None

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
            seed_count=0 if resolved.seed_only else len(resolved.seed_assets),
            proxy_name=proxy_name,
            estimated_duration_seconds=est_seconds,
            estimated_duration_human=duration_text(est_seconds),
        )

        return ScanPreview(
            target_id=target.id if data.target_id is not None else None,
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
            data, project_id, created_by
        )
        if data.new_checks is not None:
            target.new_checks = data.new_checks
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
            parent_scan_id=data.parent_scan_id,
            run_group_id=data.run_group_id,
            dimension=data.dimension,
        )
        self.session.add(scan)
        await self.session.commit()
        await self.session.refresh(scan)

        if engine.id is not None:
            await self.engine_service.touch(engine.id, project_id)
        if context is not None:
            await self.context_service.touch(context.id, project_id, scan_id=scan.id)

        await self._dispatch_batch([scan])
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
        targets = await self._batch_targets(data, project_id, created_by)
        if data.new_checks is not None:
            for target in targets:
                target.new_checks = data.new_checks

        stored = await target_seeds.load_async(
            self.session, [target.id for target in targets]
        )
        scans: list[Scan] = []
        for target in targets:
            run_engine, resolved = self._resolve_for(
                engine, context, target, proxy_url, data, stored.get(target.id)
            )
            scan = build_scan_row(
                resolved=resolved,
                engine=run_engine,
                context=context,
                target=target,
                project_id=project_id,
                created_by=created_by,
            )
            self.session.add(scan)
            scans.append(scan)

        logger.info("Creating %d scans for engine=%s", len(scans), engine.id)
        await self.session.commit()

        if engine.id is not None:
            await self.engine_service.touch(engine.id, project_id)
        if context is not None:
            await self.context_service.touch(
                context.id, project_id, scan_id=scans[-1].id
            )

        await self._dispatch_batch(scans)
        return [self._to_read(scan) for scan in scans]

    def _dispatch_scan(self, scan: Scan) -> None:
        dispatch_scan_run(str(scan.id), scan.run_epoch)

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
            scan.error = "Not queued. Check that the worker is running."
            scan.completed_at = utc_now()
        await self.session.commit()

    def _sort_expr(self, sort_by: ScanSortKey):
        if sort_by == "duration":
            end = func.coalesce(
                Scan.completed_at,
                case((Scan.status == ScanStatus.PAUSED.value, Scan.paused_at)),
                utc_now(),
            )
            return func.extract("epoch", end - Scan.started_at) - func.coalesce(
                Scan.paused_seconds, 0.0
            )
        if sort_by == "status":
            return _STATUS_RANK
        if sort_by == "subdomains":
            return Scan.subdomains_found
        if sort_by == "vulnerabilities":
            return _FINDINGS_RANK
        return func.coalesce(Scan.started_at, Scan.created_at)

    def _filter_conditions(
        self,
        m,
        statuses: list[str] | None,
        engines: list[str] | None,
        include_focused: bool = False,
    ) -> list:
        conds: list = []
        if not include_focused:
            conds.append(census_only(m))
        if statuses:
            conds.append(m.status.in_(statuses))
        if engines:
            conds.append(m.engine_name.in_(engines))
        return conds

    def build_list_query(
        self,
        project_id: UUID,
        target_ids: list[UUID] | None = None,
        statuses: list[str] | None = None,
        engines: list[str] | None = None,
        search: str | None = None,
        sort_by: ScanSortKey = "started",
        sort_dir: ScanSortDir = "desc",
        include_focused: bool = False,
        severities: list[str] | None = None,
        short: bool | None = None,
        added: bool | None = None,
        started_from: datetime | None = None,
        started_to: datetime | None = None,
        latest: bool = False,
    ) -> Select:
        query = select(Scan).where(
            Scan.project_id == project_id,
            *self._filter_conditions(Scan, statuses, engines, include_focused),
        )
        started = func.coalesce(Scan.started_at, Scan.created_at)
        if started_from is not None:
            query = query.where(started >= started_from)
        if started_to is not None:
            query = query.where(started < started_to)
        if severities:
            query = query.where(
                exists(
                    select(1).where(
                        Vulnerability.scan_id == Scan.id,
                        Vulnerability.severity.in_(severities),
                        not_(vuln_suppressed(QueryScope(()))),
                    )
                )
            )
        if short is not None:
            fell_short = exists(
                select(1).where(
                    ScanActivity.scan_id == Scan.id,
                    ScanActivity.status.in_(_SHORT),
                )
            )
            query = query.where(fell_short if short else not_(fell_short))
        if added is not None:
            grew = and_(
                exists(
                    select(1).where(
                        ScanDelta.scan_id == Scan.id,
                        ScanDelta.dimension == SurfaceDimension.WEB_ASSETS.value,
                        ScanDelta.first_seen > 0,
                    )
                ),
                self._has_earlier_run(),
            )
            query = query.where(grew if added else not_(grew))
        if target_ids:
            query = query.where(Scan.target_id.in_(target_ids))
        if search and search.strip():
            term = f"%{search.strip().lower()}%"
            query = query.join(Target, Scan.target_id == Target.id).where(
                or_(
                    func.lower(Target.target_value).like(term),
                    func.lower(Scan.engine_name).like(term),
                    func.lower(func.coalesce(Scan.context_name, "")).like(term),
                )
            )

        if latest:
            ranked = query.with_only_columns(
                Scan.id.label("id"),
                func.row_number()
                .over(partition_by=Scan.target_id, order_by=started.desc())
                .label("rn"),
            ).subquery()
            query = select(Scan).where(
                Scan.id.in_(select(ranked.c.id).where(ranked.c.rn == 1))
            )

        expr = self._sort_expr(sort_by)
        ordering = expr.asc() if sort_dir == "asc" else expr.desc()
        if sort_by == "duration":
            ordering = nullslast(ordering)
        return query.order_by(ordering, Scan.created_at.desc())

    def to_read(self, scan: Scan) -> ScanRead:
        return self._to_read(scan)

    async def new_subdomain_counts(
        self, scan_ids: list[UUID], live: Iterable[UUID] = ()
    ) -> dict[UUID, int]:
        """Per scan, the names it was the first to report for its target."""
        return await stored_deltas.first_seen(
            self.session, SurfaceDimension.WEB_ASSETS.value, scan_ids, live
        )

    async def prepare_growth(
        self, project_id: UUID, target_ids: list[UUID] | None = None
    ) -> None:
        """Store a current first-seen count for every run the list can filter on."""
        conds = [Scan.project_id == project_id]
        if target_ids:
            conds.append(Scan.target_id.in_(target_ids))
        rows = (
            await self.session.execute(select(Scan.id, Scan.status).where(*conds))
        ).all()
        await self.new_subdomain_counts(
            [r.id for r in rows],
            [r.id for r in rows if r.status in SCAN_OPEN_STATUSES],
        )

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
                census_only(),
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

    @staticmethod
    def _has_earlier_run():
        """Whether a census run of the same target started before this one."""
        earlier = aliased(Scan)
        return exists(
            select(1).where(
                earlier.target_id == Scan.target_id,
                census_only(earlier),
                tuple_(
                    func.coalesce(earlier.started_at, earlier.created_at),
                    earlier.created_at,
                )
                < tuple_(
                    func.coalesce(Scan.started_at, Scan.created_at), Scan.created_at
                ),
            )
        )

    async def first_scan_ids(self, target_ids: list[UUID]) -> set[UUID]:
        """The earliest scan id for each target."""
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
            .where(Scan.target_id.in_(target_ids), census_only())
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
        runs = scan_deltas.previous_completed(target_ids)
        pairs = (
            await self.session.execute(
                select(runs.c.id, runs.c.prev_id).where(
                    runs.c.id.in_(scan_ids), runs.c.prev_id.is_not(None)
                )
            )
        ).all()
        counts = await stored_deltas.retired(
            self.session,
            SurfaceDimension.WEB_ASSETS.value,
            [(scan_id, prev_id) for scan_id, prev_id in pairs],
        )
        return {scan_id: n for (scan_id, _), n in counts.items()}

    async def stats(
        self,
        project_id: UUID,
        target_ids: list[UUID] | None = None,
        include_focused: bool = False,
    ) -> ScanStats:
        conds = [Scan.project_id == project_id]
        if not include_focused:
            conds.append(census_only())
        if target_ids:
            conds.append(Scan.target_id.in_(target_ids))

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

        engine_rows = (
            await self.session.execute(
                select(Scan.engine_name, func.count())
                .where(*conds)
                .group_by(Scan.engine_name)
                .order_by(func.count().desc())
            )
        ).all()
        engines = [ScanFacet(name=name, count=n) for name, n in engine_rows if name]

        return ScanStats(
            total=total,
            by_status=ScanStatusCounts(**counts),
            engines=engines,
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
        new_counts = await self.new_subdomain_counts(
            scan_ids, [i.id for i in items if i.status in SCAN_OPEN_STATUSES]
        )
        gone_counts = await self.gone_subdomain_counts(scan_ids, target_ids)
        prev_counts = await self.prev_completed_counts(scan_ids, target_ids)
        first_ids = await self.first_scan_ids(target_ids)
        rescans = await self.rescan_summaries(scan_ids)
        rechecks = await self.recheck_tallies(
            [i.id for i in items if i.scope == ScanScope.FOCUSED.value]
        )
        findings = await self.finding_counts(scan_ids)
        queued = await self.queue_positions(
            [i.id for i in items if i.status == ScanStatus.PENDING.value]
        )
        for i in items:
            i.queue_position = queued.get(i.id)
            i.findings = findings.get(i.id)
            i.new_subdomains = new_counts.get(i.id, 0)
            i.gone_subdomains = gone_counts.get(i.id, 0)
            i.prev_subdomains_found = prev_counts.get(i.id)
            i.is_first_scan = i.id in first_ids
            i.rescans = rescans.get(i.id)
            i.recheck = rechecks.get(i.id)

    async def queue_positions(self, scan_ids: list[UUID]) -> dict[UUID, int]:
        """Scans ahead of each pending scan the limit holds back."""
        if not scan_ids:
            return {}
        places = dict(
            (await self.session.execute(scan_admission.positions_query(scan_ids))).all()
        )
        if not places:
            return {}
        busy = await self.session.scalar(scan_admission.running_query()) or 0
        configured = await self.session.scalar(
            select(InstanceSettings.concurrent_scans).where(
                InstanceSettings.singleton_key == SINGLETON_KEY
            )
        )
        limit = await asyncio.to_thread(scan_admission.resolve, configured)
        return {
            scan_id: place - 1
            for scan_id, place in places.items()
            if busy + place - 1 >= limit
        }

    async def finding_counts(self, scan_ids: list[UUID]) -> dict[UUID, ScanFindings]:
        """Per scan, open findings by actionable severity and whether the scan looked."""
        if not scan_ids:
            return {}
        counts = (
            await self.session.execute(
                select(Vulnerability.scan_id, Vulnerability.severity, func.count())
                .where(
                    Vulnerability.scan_id.in_(scan_ids),
                    Vulnerability.severity.in_(ACTIONABLE_SEVERITIES),
                    not_(vuln_suppressed(QueryScope(tuple(scan_ids)))),
                )
                .group_by(Vulnerability.scan_id, Vulnerability.severity)
            )
        ).all()
        wrote = set(
            (
                await self.session.execute(
                    select(Vulnerability.scan_id)
                    .where(Vulnerability.scan_id.in_(scan_ids))
                    .distinct()
                )
            ).scalars()
        )
        ran = set(
            (
                await self.session.execute(
                    select(ScanActivity.scan_id)
                    .where(
                        ScanActivity.scan_id.in_(scan_ids),
                        ScanActivity.status.in_(_RAN),
                        ScanActivity.name.in_(
                            covering_stages()[SurfaceDimension.VULNERABILITIES.value]
                        ),
                    )
                    .distinct()
                )
            ).scalars()
        )
        out = {
            sid: ScanFindings(covered=sid in wrote or sid in ran) for sid in scan_ids
        }
        for sid, severity, n in counts:
            setattr(out[sid], severity, int(n))
        return out

    async def attach_target_runs(
        self, items: list[ScanRead], include_focused: bool = False
    ) -> None:
        """Per row, how many runs its target holds."""
        target_ids = list({i.target_id for i in items})
        if not target_ids:
            return
        conds = [Scan.target_id.in_(target_ids)]
        if not include_focused:
            conds.append(census_only())
        rows = (
            await self.session.execute(
                select(Scan.target_id, func.count())
                .where(*conds)
                .group_by(Scan.target_id)
            )
        ).all()
        runs = dict(rows)
        for i in items:
            i.target_runs = int(runs.get(i.target_id, 0))

    async def latest_for_targets(
        self, project_id: UUID, target_ids: list[UUID]
    ) -> list[ScanRead]:
        """The newest census run of each target, with the fields the history rows show."""
        if not target_ids:
            return []
        started = func.coalesce(Scan.started_at, Scan.created_at)
        ranked = (
            select(
                Scan.id.label("id"),
                func.row_number()
                .over(partition_by=Scan.target_id, order_by=started.desc())
                .label("rn"),
            )
            .where(
                Scan.project_id == project_id,
                Scan.target_id.in_(target_ids),
                census_only(),
            )
            .subquery()
        )
        rows = (
            (
                await self.session.execute(
                    select(Scan).where(
                        Scan.id.in_(select(ranked.c.id).where(ranked.c.rn == 1))
                    )
                )
            )
            .scalars()
            .all()
        )
        items = [self.to_read(s) for s in rows]
        await self.attach_deltas(items)
        await self.attach_target_runs(items)
        await self._attach_covering_findings(project_id, items)
        return items

    async def _attach_covering_findings(
        self, project_id: UUID, items: list[ScanRead]
    ) -> None:
        """Replace each row's findings with its target's vulnerability covering scan."""
        if not items:
            return
        covering = dict(
            (
                await self.session.execute(
                    select(Scan.target_id, Scan.id)
                    .where(
                        Scan.project_id == project_id,
                        Scan.target_id.in_([i.target_id for i in items]),
                        census_only(),
                        covers(Vulnerability, SurfaceDimension.VULNERABILITIES.value),
                    )
                    .distinct(Scan.target_id)
                    .order_by(
                        Scan.target_id,
                        func.coalesce(Scan.started_at, Scan.created_at).desc(),
                    )
                )
            ).all()
        )
        moved = [i for i in items if covering.get(i.target_id) not in (None, i.id)]
        counts = await self.finding_counts([covering[i.target_id] for i in moved])
        for i in moved:
            sid = covering[i.target_id]
            i.findings = counts.get(sid, ScanFindings()).model_copy(
                update={"scan_id": sid}
            )

    async def finding_trends(
        self, project_id: UUID, target_ids: list[UUID], limit: int = TREND_POINTS
    ) -> list[ScanTargetTrend]:
        """Per target, open findings of its last completed census runs, oldest first."""
        if not target_ids:
            return []
        started = func.coalesce(Scan.started_at, Scan.created_at)
        rn = (
            func.row_number()
            .over(partition_by=Scan.target_id, order_by=started.desc())
            .label("rn")
        )
        ranked = (
            select(
                Scan.id.label("id"),
                Scan.target_id.label("target_id"),
                started.label("at"),
                rn,
            )
            .where(
                Scan.project_id == project_id,
                Scan.target_id.in_(target_ids),
                Scan.status == ScanStatus.COMPLETED.value,
                census_only(),
            )
            .subquery()
        )
        runs = (
            await self.session.execute(
                select(ranked.c.id, ranked.c.target_id, ranked.c.at)
                .where(ranked.c.rn <= limit)
                .order_by(ranked.c.target_id, ranked.c.at.asc())
            )
        ).all()
        counts = await self.finding_counts([r.id for r in runs])
        out: dict[UUID, ScanTargetTrend] = {
            tid: ScanTargetTrend(target_id=tid) for tid in target_ids
        }
        for r in runs:
            c = counts.get(r.id) or ScanFindings()
            out[r.target_id].points.append(
                ScanTrendPoint(
                    scan_id=r.id,
                    started_at=r.at,
                    critical=c.critical,
                    high=c.high,
                    medium=c.medium,
                )
            )
        return list(out.values())

    async def daily(
        self,
        project_id: UUID,
        days: int,
        target_ids: list[UUID] | None = None,
        include_focused: bool = False,
    ) -> ScanDaily:
        """Runs per UTC day over the days a sliding window touches, and its totals."""
        days = max(1, min(days, MAX_DAILY_WINDOW))
        cutoff = utc_now() - timedelta(days=days)
        since = cutoff.replace(hour=0, minute=0, second=0, microsecond=0)
        started = func.coalesce(Scan.started_at, Scan.created_at)
        conds = [Scan.project_id == project_id, started >= since]
        if target_ids:
            conds.append(Scan.target_id.in_(target_ids))
        if not include_focused:
            conds.append(census_only())
        runs = (
            await self.session.execute(
                select(Scan.id, Scan.status, started.label("at")).where(*conds)
            )
        ).all()
        counts = await self.finding_counts([r.id for r in runs])
        out = {
            (since + timedelta(days=n)).date(): ScanDay(day=since + timedelta(days=n))
            for n in range(days + 1)
        }
        window = ScanDay(day=cutoff)
        for r in runs:
            buckets = [out.get(r.at.astimezone(since.tzinfo).date())]
            if r.at >= cutoff:
                buckets.append(window)
            for day in buckets:
                if day is None:
                    continue
                day.runs += 1
                if r.status == ScanStatus.FAILED.value:
                    day.failed += 1
                c = counts.get(r.id)
                if c is None:
                    continue
                for severity in ACTIONABLE_SEVERITIES:
                    if getattr(c, severity):
                        setattr(day, severity, getattr(day, severity) + 1)
        return ScanDaily(since=cutoff, days=list(out.values()), window=window)

    async def recheck_tallies(self, scan_ids: list[UUID]) -> dict[UUID, RecheckTally]:
        """Per focused run, the assets it rechecked and which fields moved."""
        if not scan_ids:
            return {}
        rows = (
            await self.session.execute(
                select(
                    AssetRecheck.scan_id,
                    func.count(),
                    func.count().filter(AssetRecheck.changed.is_(True)),
                )
                .where(AssetRecheck.scan_id.in_(scan_ids))
                .group_by(AssetRecheck.scan_id)
            )
        ).all()
        tallies = {
            scan_id: RecheckTally(assets=assets, changed=changed)
            for scan_id, assets, changed in rows
        }
        for scan_id, fields in (await self._recheck_fields(scan_ids)).items():
            if scan_id in tallies:
                tallies[scan_id].fields = fields
        return tallies

    async def _recheck_fields(
        self, scan_ids: list[UUID]
    ) -> dict[UUID, list[RecheckFieldCount]]:
        """Fold every asset's change list into one count per field and direction."""
        change = (
            func.jsonb_array_elements(cast(AssetRecheck.changes, JSONB))
            .table_valued(column("value", JSONB))
            .lateral()
        )
        value = change.c.value
        rows = (
            await self.session.execute(
                select(
                    AssetRecheck.scan_id,
                    value["field"].astext.label("field"),
                    value["label"].astext.label("label"),
                    value["tone"].astext.label("tone"),
                    func.count(),
                )
                .select_from(AssetRecheck)
                .join(change, true())
                .where(AssetRecheck.scan_id.in_(scan_ids))
                .group_by(AssetRecheck.scan_id, "field", "label", "tone")
            )
        ).all()
        out: dict[UUID, dict[str, RecheckFieldCount]] = {}
        for scan_id, field, label, tone, count in rows:
            if not field:
                continue
            by_field = out.setdefault(scan_id, {})
            entry = by_field.setdefault(
                field,
                RecheckFieldCount(
                    field=field,
                    label=label or field,
                    dimension=change_dimension(field),
                ),
            )
            if tone == Tone.DOWN.value:
                entry.down += count
            else:
                entry.up += count
        return {
            scan_id: sorted(
                by_field.values(), key=lambda f: (-(f.up + f.down), f.label)
            )
            for scan_id, by_field in out.items()
        }

    async def rescan_summaries(
        self, parent_ids: list[UUID]
    ) -> dict[UUID, RescanSummary]:
        if not parent_ids:
            return {}
        rows = (
            await self.session.execute(
                select(Scan.parent_scan_id, Scan.status, func.count())
                .where(Scan.parent_scan_id.in_(parent_ids))
                .group_by(Scan.parent_scan_id, Scan.status)
            )
        ).all()
        out: dict[UUID, RescanSummary] = {}
        for parent_id, status_value, count in rows:
            summary = out.setdefault(parent_id, RescanSummary(total=0))
            summary.total += count
            if status_value in SCAN_LIVE_STATUSES:
                summary.running += count
            elif status_value == ScanStatus.FAILED.value:
                summary.failed += count
        return out

    async def _get_scan(self, id: UUID, project_id: UUID, lock: bool = False) -> Scan:
        statement = select(Scan).where(Scan.id == id, Scan.project_id == project_id)
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        scan = result.scalar_one_or_none()
        if not scan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found"
            )
        return scan

    async def cancel(self, id: UUID, project_id: UUID) -> ScanRead:
        scan = await self._get_scan(id, project_id, lock=True)
        if scan.status in SCAN_OPEN_STATUSES:
            held = scan.status == ScanStatus.RUNNING.value
            scan.status = ScanStatus.CANCELLED.value
            scan.completed_at = utc_now()
            fold_pause(scan, scan.completed_at)
            scan.error = "Cancelled by user."
            await self.session.commit()

            now = utc_now()
            for model in (ScanActivity, ScanCommand):
                await self.session.execute(
                    update(model)
                    .where(
                        model.scan_id == scan.id,
                        model.status.in_(_UNSETTLED_ACTIVITY_STATUSES),
                    )
                    .values(status=ScanActivityStatus.ABORTED.value, completed_at=now)
                )
            await self.session.commit()
            try:
                await asyncio.to_thread(dispatch_scan_finalize, str(scan.id))
            except Exception:
                logger.warning("cancel finalize dispatch failed", exc_info=True)
            if held:
                await self._admit_waiting()
            await self._announce_cancelled(scan)
            await self.session.refresh(scan)
        return self._to_read(scan)

    async def cancel_all(
        self, project_id: UUID, target_ids: list[UUID] | None = None
    ) -> ScanCancelAll:
        conds = [Scan.project_id == project_id, Scan.status.in_(SCAN_OPEN_STATUSES)]
        if target_ids:
            conds.append(Scan.target_id.in_(target_ids))
        ids = (
            (await self.session.execute(select(Scan.id).where(*conds))).scalars().all()
        )
        cancelled = 0
        for scan_id in ids:
            read = await self.cancel(id=scan_id, project_id=project_id)
            if read.status == ScanStatus.CANCELLED.value:
                cancelled += 1
        return ScanCancelAll(cancelled=cancelled)

    async def pause(self, id: UUID, project_id: UUID) -> ScanRead:
        """Stop the run where it stands."""
        scan = await self._get_scan(id, project_id, lock=True)
        if scan.status != ScanStatus.RUNNING.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="The scan is not running."
            )
        if (scan.execution_config or {}).get(WATCH_HOST_KEY):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A watch probe cannot be paused. Cancel it to stop the run.",
            )
        now = utc_now()
        scan.status = ScanStatus.PAUSED.value
        scan.paused_at = now
        stopped = (
            await self.session.execute(
                update(ScanActivity)
                .where(
                    ScanActivity.scan_id == scan.id,
                    ScanActivity.status == ScanActivityStatus.RUNNING.value,
                )
                .values(status=ScanActivityStatus.PAUSED.value)
            )
        ).rowcount
        await self.session.execute(
            update(ScanCommand)
            .where(
                ScanCommand.scan_id == scan.id,
                ScanCommand.status == ScanActivityStatus.RUNNING.value,
            )
            .values(status=ScanActivityStatus.ABORTED.value, completed_at=now)
        )
        await self._log_paused(scan, stopped)
        await self.session.commit()

        await asyncio.to_thread(revoke_scan_tasks, scan.celery_task_ids or [])
        await self._admit_waiting()
        await self._announce_paused(scan, stopped)
        await self.session.refresh(scan)
        return self._to_read(scan)

    async def resume(self, id: UUID, project_id: UUID) -> ScanRead:
        """Move the run back to RUNNING and dispatch the resume."""
        scan = await self._get_scan(id, project_id, lock=True)
        if scan.status != ScanStatus.PAUSED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="The scan is not paused."
            )
        now = utc_now()
        paused_at = scan.paused_at
        paused_seconds = scan.paused_seconds
        left = await self._stages_left(scan)
        fold_pause(scan, now)
        scan.status = ScanStatus.RUNNING.value
        scan.error = None
        scan.run_epoch = epoch = (scan.run_epoch or 0) + 1
        await self._log_resumed(scan, left)
        await self.session.commit()

        try:
            await asyncio.to_thread(dispatch_scan_resume, str(scan.id), epoch)
        except Exception:
            logger.warning("scan resume dispatch failed", exc_info=True)
            scan.status = ScanStatus.PAUSED.value
            scan.paused_at = paused_at or now
            scan.paused_seconds = paused_seconds
            await self.session.commit()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="The scan was not resumed. Check that the worker service is running.",
            ) from None
        await self._announce_resumed(scan, left)
        await self.session.refresh(scan)
        return self._to_read(scan)

    async def _stages_left(self, scan: Scan) -> int:
        rows = (
            (
                await self.session.execute(
                    select(ScanActivity).where(ScanActivity.scan_id == scan.id)
                )
            )
            .scalars()
            .all()
        )
        return resume_point(list(rows))[2]

    async def _log_resumed(self, scan: Scan, left: int) -> None:
        target_value = (scan.execution_config or {}).get("target_value", "")
        await ActivityLogService(self.session).log_async(
            event=ActivityEvent.SCAN_RESUMED,
            title=f"Scan resumed · {target_value}",
            description=f"{left} {'stage' if left == 1 else 'stages'} remaining",
            level=ActivityLevel.INFO,
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            target_value=target_value,
        )

    async def _announce(
        self, scan: Scan, emit: Callable[[ScanEventPublisher], None]
    ) -> None:
        scan_id, project_id = str(scan.id), str(scan.project_id)

        def publish() -> None:
            emit(ScanEventPublisher(scan_id=scan_id, project_id=project_id))

        try:
            await asyncio.to_thread(publish)
        except Exception:
            logger.debug("scan event emit failed", exc_info=True)

    async def _announce_resumed(self, scan: Scan, left: int) -> None:
        await self._announce(
            scan,
            lambda p: p.scan_resumed(status=ScanStatus.RUNNING.value, stages_left=left),
        )

    async def _log_paused(self, scan: Scan, stopped: int) -> None:
        target_value = (scan.execution_config or {}).get("target_value", "")
        await ActivityLogService(self.session).log_async(
            event=ActivityEvent.SCAN_PAUSED,
            title=f"Scan paused · {target_value}",
            description=f"{stopped} stage{'s' if stopped != 1 else ''} stopped"
            if stopped
            else None,
            level=ActivityLevel.INFO,
            project_id=scan.project_id,
            target_id=scan.target_id,
            scan_id=scan.id,
            target_value=target_value,
        )

    async def _announce_paused(self, scan: Scan, stopped: int) -> None:
        await self._announce(
            scan,
            lambda p: p.scan_paused(
                status=ScanStatus.PAUSED.value, stages_stopped=stopped
            ),
        )

    async def _announce_cancelled(self, scan: Scan) -> None:
        await self._announce(
            scan, lambda p: p.scan_cancelled(status=ScanStatus.CANCELLED.value)
        )

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
        out: list[ScanActivityRead] = []
        for a in rows:
            read = ScanActivityRead.model_validate(a, from_attributes=True)
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
        held = scan.status == ScanStatus.RUNNING.value
        if scan.status in SCAN_OPEN_STATUSES:
            await asyncio.to_thread(revoke_scan_tasks, scan.celery_task_ids or [])
        await self.session.delete(scan)
        await self.session.commit()
        if held:
            await self._admit_waiting()

    async def _admit_waiting(self) -> None:
        try:
            await asyncio.to_thread(dispatch_scan_admission)
        except Exception:
            logger.warning("scan admission dispatch failed", exc_info=True)

    def _to_read(self, scan: Scan) -> ScanRead:
        cfg = copy.deepcopy(scan.execution_config or {})
        cfg.pop("_auth_header_names", None)
        auth = cfg.pop("_auth", None) or {"auth_type": AuthType.NONE.value}
        masked = _mask_config_headers(cfg)
        resolved = _resolved_config(scan.id, masked)
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
            scope=scan.scope,
            parent_scan_id=scan.parent_scan_id,
            run_group_id=scan.run_group_id,
            seed_count=len((scan.execution_config or {}).get("seed_assets") or []),
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
            paused_at=scan.paused_at,
            paused_seconds=scan.paused_seconds or 0.0,
            duration_seconds=scan_duration(scan),
        )
