"""Tripwires: stored, previewed against settled runs, and their checks read back."""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from app.services.asset_query.ast import QuerySyntaxError
from app.services.target_names import target_names
from shared.definitions.rescan import RESCANNABLE_STAGES, stages_for
from shared.definitions.surface import SURFACE_LABELS, SURFACE_NOUN, SURFACE_ORDER
from shared.definitions.tripwires import (
    ACTION_HELP,
    ACTION_LABELS,
    ACTION_ORDER,
    FIRE_ON_HELP,
    FIRE_ON_LABELS,
    FIRE_ON_ORDER,
    MAX_BACKTEST_RUNS,
    MAX_PREVIEW_TARGETS,
    MAX_RUNS_PER_DAY,
    MAX_TRIPWIRES,
    PREVIEW_ROW_CAP,
    RECENT_DAYS,
    TEMPLATE_GROUPS,
    TEMPLATES,
    TRIGGER_HELP,
    TRIGGER_LABELS,
    TRIGGER_ORDER,
    ActionKind,
    CheckStatus,
    ScopeKind,
    template_group,
)
from shared.enums.scan import SCAN_TERMINAL_STATUSES
from shared.models.asset_query import QueryError
from shared.models.notification_channel import NotificationChannel
from shared.models.organization import Organization
from shared.models.scan import Scan
from shared.models.tag import Tag, TargetTag
from shared.models.target import Target, TargetOrganization
from shared.models.tripwire import (
    ChannelChoice,
    ChoiceSpec,
    FiredRow,
    Outcome,
    PreviewTarget,
    StageChoice,
    TemplateRead,
    Tripwire,
    TripwireBacktest,
    TripwireCatalog,
    TripwireCreate,
    TripwireDimension,
    TripwirePreview,
    TripwirePreviewRequest,
    TripwireRead,
    TripwireRun,
    TripwireRunCounts,
    TripwireRunRead,
    TripwireScope,
    TripwireScopeRead,
    TripwireUpdate,
)
from shared.services.asset_query.errors import (
    NO_JIT,
    STATEMENT_TIMEOUT,
    query_error_for,
    syntax_error,
)
from shared.services.scan_deltas import TABLES
from shared.services.scan_scope import census_only, covers
from shared.services.tripwires import Evaluation, evaluate, validate_query
from shared.services.tripwires.actions import parse_actions
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

QUERY_FAILED = "The query did not run."
PREVIEW_ROWS = 20


class TripwireError(ValueError):
    """The tripwire cannot be stored as written."""


def _started():
    return func.coalesce(Scan.started_at, Scan.created_at)


def catalog_stages() -> list[StageChoice]:
    from stages.registry import stage_by_name  # noqa: PLC0415

    known = stage_by_name()
    return [
        StageChoice(name=name, title=known[name].title)
        for name in sorted(RESCANNABLE_STAGES)
        if name in known
    ]


class TripwireService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------- reads ----------

    async def _get(
        self, tripwire_id: uuid.UUID, project_id: uuid.UUID
    ) -> Tripwire | None:
        row = await self.session.get(Tripwire, tripwire_id)
        if row is None or row.project_id != project_id:
            return None
        return row

    async def get(
        self, tripwire_id: uuid.UUID, project_id: uuid.UUID
    ) -> TripwireRead | None:
        row = await self._get(tripwire_id, project_id)
        if row is None:
            return None
        return (await self._reads([row]))[0]

    async def list(self, project_id: uuid.UUID) -> list[TripwireRead]:
        rows = (
            (
                await self.session.execute(
                    select(Tripwire)
                    .where(Tripwire.project_id == project_id)
                    .order_by(Tripwire.created_at.desc())
                )
            )
            .scalars()
            .all()
        )
        return await self._reads(list(rows))

    async def _reads(self, rows: list[Tripwire]) -> list[TripwireRead]:
        if not rows:
            return []
        since = utc_now() - timedelta(days=RECENT_DAYS)
        recent = dict(
            (
                await self.session.execute(
                    select(TripwireRun.tripwire_id, func.count())
                    .where(
                        TripwireRun.tripwire_id.in_([r.id for r in rows]),
                        TripwireRun.status == CheckStatus.FIRED.value,
                        TripwireRun.fired_at >= since,
                    )
                    .group_by(TripwireRun.tripwire_id)
                )
            ).all()
        )
        labels = await self._scope_labels(rows)
        return [
            TripwireRead(
                id=row.id,
                project_id=row.project_id,
                name=row.name,
                dimension=row.dimension,
                query=row.query,
                trigger=row.trigger,
                fire_on=row.fire_on,
                scope=TripwireScopeRead(
                    kind=row.scope_kind,
                    ids=[uuid.UUID(str(i)) for i in (row.scope_ids or [])],
                    labels=labels.get(row.id, []),
                ),
                actions=parse_actions(row.actions),
                enabled=row.enabled,
                fired_count=row.fired_count,
                recent_fired=int(recent.get(row.id, 0)),
                last_fired_at=row.last_fired_at,
                last_checked_at=row.last_checked_at,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    async def _scope_labels(self, rows: list[Tripwire]) -> dict[uuid.UUID, list[str]]:
        wanted: dict[str, set[uuid.UUID]] = {
            ScopeKind.TARGETS.value: set(),
            ScopeKind.ORGANIZATION.value: set(),
            ScopeKind.TAG.value: set(),
        }
        for row in rows:
            if row.scope_kind in wanted:
                wanted[row.scope_kind].update(
                    uuid.UUID(str(i)) for i in row.scope_ids or []
                )
        names: dict[str, dict[uuid.UUID, str]] = {
            ScopeKind.TARGETS.value: await target_names(
                self.session, wanted[ScopeKind.TARGETS.value]
            ),
            ScopeKind.ORGANIZATION.value: await self._names(
                Organization, wanted[ScopeKind.ORGANIZATION.value]
            ),
            ScopeKind.TAG.value: await self._names(Tag, wanted[ScopeKind.TAG.value]),
        }
        out: dict[uuid.UUID, list[str]] = {}
        for row in rows:
            lookup = names.get(row.scope_kind)
            if lookup is None:
                continue
            out[row.id] = [
                lookup[i]
                for i in (uuid.UUID(str(v)) for v in row.scope_ids or [])
                if i in lookup
            ]
        return out

    async def _names(self, model, ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
        if not ids:
            return {}
        rows = await self.session.execute(
            select(model.id, model.name).where(model.id.in_(ids))
        )
        return {row[0]: row[1] for row in rows.all()}

    # ---------- writes ----------

    async def create(
        self, payload: TripwireCreate, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> TripwireRead:
        total = await self.session.scalar(
            select(func.count(Tripwire.id)).where(Tripwire.project_id == project_id)
        )
        if int(total or 0) >= MAX_TRIPWIRES:
            msg = f"A project may hold {MAX_TRIPWIRES} tripwires."
            raise TripwireError(msg)
        self._check_query(payload.dimension, payload.query)
        await self._check_scope(payload.scope, project_id)
        await self._check_actions(payload.actions)
        row = Tripwire(
            project_id=project_id,
            name=payload.name,
            dimension=payload.dimension,
            query=payload.query.strip(),
            trigger=payload.trigger,
            fire_on=payload.fire_on,
            scope_kind=payload.scope.kind,
            scope_ids=[str(i) for i in payload.scope.ids],
            actions=[a.model_dump(mode="json") for a in payload.actions],
            enabled=payload.enabled,
            created_by=user_id,
        )
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return (await self._reads([row]))[0]

    async def update(
        self, tripwire_id: uuid.UUID, payload: TripwireUpdate, project_id: uuid.UUID
    ) -> TripwireRead | None:
        row = await self._get(tripwire_id, project_id)
        if row is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        dimension = data.get("dimension", row.dimension)
        query = data.get("query", row.query)
        if "dimension" in data or "query" in data:
            self._check_query(dimension, query or "")
        if payload.scope is not None:
            await self._check_scope(payload.scope, project_id)
            row.scope_kind = payload.scope.kind
            row.scope_ids = [str(i) for i in payload.scope.ids]
        if payload.actions is not None:
            await self._check_actions(payload.actions)
            row.actions = [a.model_dump(mode="json") for a in payload.actions]
        for key in ("name", "dimension", "trigger", "fire_on", "enabled"):
            if data.get(key) is not None:
                setattr(row, key, data[key])
        if "query" in data and data["query"] is not None:
            row.query = data["query"].strip()
        row.updated_at = utc_now()
        self.session.add(row)
        await self.session.commit()
        await self.session.refresh(row)
        return (await self._reads([row]))[0]

    async def delete(self, tripwire_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        row = await self._get(tripwire_id, project_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.commit()
        return True

    def _check_query(self, dimension: str, query: str) -> None:
        try:
            validate_query(dimension, query)
        except QuerySyntaxError as exc:
            raise TripwireError(exc.message) from exc

    async def _check_scope(self, scope: TripwireScope, project_id: uuid.UUID) -> None:
        if scope.kind == ScopeKind.ALL.value:
            return
        model = {
            ScopeKind.TARGETS.value: Target,
            ScopeKind.ORGANIZATION.value: Organization,
            ScopeKind.TAG.value: Tag,
        }[scope.kind]
        found = set(
            await self.session.scalars(
                select(model.id).where(
                    model.id.in_(scope.ids), model.project_id == project_id
                )
            )
        )
        missing = [str(i) for i in scope.ids if i not in found]
        if missing:
            msg = f"Not in this project: {', '.join(missing[:3])}."
            raise TripwireError(msg)

    async def _check_actions(self, actions) -> None:
        for action in actions:
            if action.kind == ActionKind.NOTIFY.value and action.channel_ids:
                found = set(
                    await self.session.scalars(
                        select(NotificationChannel.id).where(
                            NotificationChannel.id.in_(action.channel_ids)
                        )
                    )
                )
                if found != set(action.channel_ids):
                    msg = "A chosen notification channel does not exist."
                    raise TripwireError(msg)
            if action.kind == ActionKind.SCAN.value:
                unknown = [s for s in action.stages if s not in RESCANNABLE_STAGES]
                if unknown:
                    msg = f"Not a stage a focused run can re-run: {', '.join(unknown)}."
                    raise TripwireError(msg)

    # ---------- checks ----------

    async def runs(
        self, tripwire_id: uuid.UUID, project_id: uuid.UUID, status: str | None
    ):
        """The statement the paginated history reads."""
        query = select(TripwireRun).where(
            TripwireRun.tripwire_id == tripwire_id,
            TripwireRun.project_id == project_id,
        )
        if status == CheckStatus.FIRED.value:
            query = query.where(TripwireRun.status == CheckStatus.FIRED.value)
        elif status == CheckStatus.QUIET.value:
            query = query.where(TripwireRun.status != CheckStatus.FIRED.value)
        return query.order_by(TripwireRun.checked_at.desc(), TripwireRun.id.desc())

    async def counts(
        self, tripwire_id: uuid.UUID, project_id: uuid.UUID
    ) -> TripwireRunCounts:
        rows = (
            await self.session.execute(
                select(TripwireRun.status, func.count())
                .where(
                    TripwireRun.tripwire_id == tripwire_id,
                    TripwireRun.project_id == project_id,
                )
                .group_by(TripwireRun.status)
            )
        ).all()
        by_status = {status: int(n) for status, n in rows}
        fired = by_status.get(CheckStatus.FIRED.value, 0)
        total = sum(by_status.values())
        return TripwireRunCounts(fired=fired, quiet=total - fired, total=total)

    async def run(
        self, run_id: uuid.UUID, project_id: uuid.UUID
    ) -> TripwireRunRead | None:
        row = await self.session.get(TripwireRun, run_id)
        if row is None or row.project_id != project_id:
            return None
        return (await self.run_reads([row]))[0]

    async def run_reads(self, rows: list[TripwireRun]) -> list[TripwireRunRead]:
        names = await target_names(self.session, [r.target_id for r in rows])
        return [
            TripwireRunRead(
                id=row.id,
                tripwire_id=row.tripwire_id,
                target_id=row.target_id,
                target_value=names.get(row.target_id, ""),
                scan_id=row.scan_id,
                status=row.status,
                matched=row.matched,
                fired=row.fired,
                rows=[FiredRow.model_validate(r) for r in row.rows or []],
                outcomes=[Outcome.model_validate(o) for o in row.outcomes or []],
                detail=row.detail,
                checked_at=row.checked_at,
                fired_at=row.fired_at,
            )
            for row in rows
        ]

    # ---------- preview ----------

    async def _scoped_targets(
        self, scope: TripwireScope, project_id: uuid.UUID
    ) -> list[uuid.UUID]:
        query = select(Target.id).where(Target.project_id == project_id)
        if scope.kind == ScopeKind.TARGETS.value:
            query = query.where(Target.id.in_(scope.ids))
        elif scope.kind == ScopeKind.ORGANIZATION.value:
            query = query.where(
                Target.id.in_(
                    select(TargetOrganization.target_id).where(
                        TargetOrganization.organization_id.in_(scope.ids)
                    )
                )
            )
        elif scope.kind == ScopeKind.TAG.value:
            query = query.where(
                Target.id.in_(
                    select(TargetTag.target_id).where(TargetTag.tag_id.in_(scope.ids))
                )
            )
        return list(await self.session.scalars(query))

    def _settled(self, dimension: str, targets: list[uuid.UUID]):
        return select(Scan).where(
            Scan.target_id.in_(targets),
            census_only(),
            Scan.status.in_(SCAN_TERMINAL_STATUSES),
            covers(TABLES[dimension], dimension),
        )

    async def _latest_scans(
        self, dimension: str, targets: list[uuid.UUID]
    ) -> list[Scan]:
        if not targets:
            return []
        rows = await self.session.execute(
            self._settled(dimension, targets)
            .distinct(Scan.target_id)
            .order_by(Scan.target_id, _started().desc())
        )
        scans = sorted(
            rows.scalars().all(),
            key=lambda s: s.started_at or s.created_at,
            reverse=True,
        )
        return scans[:MAX_PREVIEW_TARGETS]

    async def _recent_scans(
        self, dimension: str, targets: list[uuid.UUID]
    ) -> tuple[list[Scan], bool]:
        if not targets:
            return [], False
        since = utc_now() - timedelta(days=RECENT_DAYS)
        rows = await self.session.execute(
            self._settled(dimension, targets)
            .where(_started() >= since)
            .order_by(_started().desc())
            .limit(MAX_BACKTEST_RUNS + 1)
        )
        scans = list(rows.scalars().all())
        return scans[:MAX_BACKTEST_RUNS], len(scans) > MAX_BACKTEST_RUNS

    async def _evaluate(
        self, payload: TripwirePreviewRequest, scan: Scan
    ) -> Evaluation:
        now = utc_now()
        return await self.session.run_sync(
            lambda sync: evaluate(
                sync,
                dimension=payload.dimension,
                query=payload.query,
                fire_on=payload.fire_on,
                scan=scan,
                now=now,
                cap=PREVIEW_ROW_CAP,
                strict=False,
            )
        )

    @staticmethod
    def _row(scan: Scan, names: dict, result: Evaluation) -> PreviewTarget:
        return PreviewTarget(
            target_id=scan.target_id,
            target_value=names.get(scan.target_id, ""),
            scan_id=scan.id,
            status=result.status,
            matched=result.matched,
            fired=len(result.fired),
            capped=result.capped,
            completed_at=scan.completed_at,
        )

    async def _prepare(self, payload: TripwirePreviewRequest) -> QueryError | None:
        try:
            validate_query(payload.dimension, payload.query)
        except QuerySyntaxError as exc:
            return syntax_error(exc)
        await self.session.execute(text(STATEMENT_TIMEOUT))
        await self.session.execute(text(NO_JIT))
        return None

    async def preview(
        self, payload: TripwirePreviewRequest, project_id: uuid.UUID
    ) -> TripwirePreview:
        """The latest settled run of each target in scope, evaluated as the tripwire would be."""
        error = await self._prepare(payload)
        if error:
            return TripwirePreview(error=error)
        targets = await self._scoped_targets(payload.scope, project_id)
        scans = await self._latest_scans(payload.dimension, targets)
        names = await target_names(self.session, [s.target_id for s in scans])
        out = TripwirePreview(unscanned=len(targets) - len(scans))
        for scan in scans:
            try:
                result = await self._evaluate(payload, scan)
            except DBAPIError as exc:
                await self.session.rollback()
                rejected = query_error_for(exc)
                if rejected is None:
                    raise
                return TripwirePreview(error=rejected)
            out.targets.append(self._row(scan, names, result))
            out.matched += result.matched
            out.fired += len(result.fired)
            out.capped = out.capped or result.capped
            if len(out.rows) < PREVIEW_ROWS:
                out.rows.extend(result.fired[: PREVIEW_ROWS - len(out.rows)])
        return out

    async def backtest(
        self, payload: TripwirePreviewRequest, project_id: uuid.UUID
    ) -> TripwireBacktest:
        """Every settled run of the window, newest first, evaluated as the tripwire would be."""
        error = await self._prepare(payload)
        if error:
            return TripwireBacktest(days=RECENT_DAYS, error=error)
        targets = await self._scoped_targets(payload.scope, project_id)
        scans, capped = await self._recent_scans(payload.dimension, targets)
        names = await target_names(self.session, [s.target_id for s in scans])
        out = TripwireBacktest(days=RECENT_DAYS, capped=capped)
        for scan in scans:
            try:
                result = await self._evaluate(payload, scan)
            except DBAPIError as exc:
                await self.session.rollback()
                rejected = query_error_for(exc)
                if rejected is None:
                    raise
                return TripwireBacktest(days=RECENT_DAYS, error=rejected)
            out.runs.append(self._row(scan, names, result))
        return out

    # ---------- catalog ----------

    async def catalog(self) -> TripwireCatalog:
        channels = (
            await self.session.execute(
                select(NotificationChannel)
                .where(NotificationChannel.is_active.is_(True))
                .order_by(NotificationChannel.name)
            )
        ).scalars()
        return TripwireCatalog(
            dimensions=[
                TripwireDimension(
                    key=key,
                    label=SURFACE_LABELS[key],
                    noun=SURFACE_NOUN[key][0],
                    noun_plural=SURFACE_NOUN[key][1],
                    default_stages=list(stages_for(key)),
                )
                for key in SURFACE_ORDER
            ],
            triggers=[
                ChoiceSpec(key=k, label=TRIGGER_LABELS[k], help=TRIGGER_HELP[k])
                for k in TRIGGER_ORDER
            ],
            fire_modes=[
                ChoiceSpec(key=k, label=FIRE_ON_LABELS[k], help=FIRE_ON_HELP[k])
                for k in FIRE_ON_ORDER
            ],
            actions=[
                ChoiceSpec(key=k, label=ACTION_LABELS[k], help=ACTION_HELP[k])
                for k in ACTION_ORDER
            ],
            stages=catalog_stages(),
            templates=[
                TemplateRead(
                    key=t.key,
                    name=t.name,
                    dimension=t.dimension,
                    query=t.query,
                    fire_on=t.fire_on,
                    trigger=t.trigger,
                    group=template_group(t),
                )
                for t in TEMPLATES
            ],
            template_groups=[
                ChoiceSpec(key=key, label=label) for key, label in TEMPLATE_GROUPS
            ],
            channels=[
                ChannelChoice(id=c.id, name=c.name, provider=c.provider)
                for c in channels
            ],
            max_tripwires=MAX_TRIPWIRES,
            max_runs_per_day=MAX_RUNS_PER_DAY,
            recent_days=RECENT_DAYS,
        )


__all__ = ["TripwireError", "TripwireService", "catalog_stages"]
