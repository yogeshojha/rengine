"""Read side of the account's own reports and bounties."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from shared.definitions.bounty_programs import PLATFORMS_BY_KEY, PlatformSpec
from shared.definitions.bounty_reports import (
    REPORT_SEVERITIES,
    REPORT_STAGE_LABELS,
    REPORT_STATES,
    SETTLED_STATES,
    ReportSort,
    ReportStage,
    report_state,
    stage_states,
)
from shared.models.bounty_program import BountyProgram
from shared.models.bounty_report import (
    AwardRead,
    BountyAccount,
    BountyAccountSummary,
    BountyAward,
    BountyReport,
    BountyReportRead,
    Money,
    MonthPoint,
    ProgramReports,
    ReportStateCount,
    SeverityCount,
)

_TOTAL = BountyAward.amount + BountyAward.bonus
MONTHS = 12


def tracked_platform(platform: str) -> PlatformSpec:
    spec = PLATFORMS_BY_KEY.get(platform)
    if not spec or not spec.tracks_reports:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{spec.label if spec else platform} has no report API.",
        )
    return spec


def _paid(platform: str):
    return (
        select(BountyAward.id)
        .where(
            BountyAward.platform == platform,
            BountyAward.report_external_id == BountyReport.external_id,
        )
        .exists()
    )


def _stage_of(column, stage: str):
    """Stage predicate matching `report_state`."""
    if stage == ReportStage.OPEN.value:
        return column.not_in(SETTLED_STATES)
    return column.in_(stage_states(stage))


def _in_stage(stage: str):
    return _stage_of(col(BountyReport.state), stage)


def _severity_rank():
    return case(
        {s: i for i, s in enumerate(REPORT_SEVERITIES)},
        value=BountyReport.severity,
        else_=len(REPORT_SEVERITIES),
    )


class BountyReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _rows(self, stmt) -> list[tuple]:
        return list((await self.session.execute(stmt)).tuples().all())

    async def _names(self, platform: str, handles: set[str]) -> dict[str, str]:
        """Program names from the Bounty Hub, then from awards."""
        if not handles:
            return {}
        ordered = sorted(handles)
        names = dict(
            await self._rows(
                select(BountyAward.program_handle, func.max(BountyAward.program_name))
                .where(
                    BountyAward.platform == platform,
                    col(BountyAward.program_handle).in_(ordered),
                    col(BountyAward.program_name).is_not(None),
                )
                .group_by(BountyAward.program_handle)
            )
        )
        names.update(await self._hub(platform, handles))
        return names

    async def _hub(self, platform: str, handles: set[str]) -> dict[str, str]:
        if not handles:
            return {}
        return dict(
            await self._rows(
                select(BountyProgram.handle, BountyProgram.name).where(
                    BountyProgram.platform == platform,
                    col(BountyProgram.handle).in_(sorted(handles)),
                )
            )
        )

    async def summary(self, spec: PlatformSpec) -> BountyAccountSummary:
        platform = spec.key
        account = await self.session.get(BountyAccount, platform)
        reports = BountyReport.platform == platform
        awards = BountyAward.platform == platform

        counts = dict(
            await self._rows(
                select(BountyReport.state, func.count())
                .where(reports)
                .group_by(BountyReport.state)
            )
        )
        order = {s.key: i for i, s in enumerate(REPORT_STATES)}
        states = [
            ReportStateCount(
                state=key,
                label=report_state(key).label,
                stage=report_state(key).stage.value,
                count=n,
            )
            for key, n in sorted(counts.items(), key=lambda kv: order.get(kv[0], 99))
        ]
        stages = dict.fromkeys(REPORT_STAGE_LABELS, 0)
        for s in states:
            stages[s.stage] = stages.get(s.stage, 0) + s.count

        by_severity = dict(
            await self._rows(
                select(BountyReport.severity, func.count())
                .where(reports, col(BountyReport.severity).is_not(None))
                .group_by(BountyReport.severity)
            )
        )
        severities = [
            SeverityCount(severity=s, count=by_severity[s])
            for s in REPORT_SEVERITIES
            if by_severity.get(s)
        ]

        totals = (
            await self.session.execute(
                select(
                    func.count(),
                    func.count(func.distinct(BountyReport.program_handle)),
                    func.min(BountyReport.submitted_at),
                    func.max(BountyReport.submitted_at),
                    func.count().filter(_paid(platform)),
                ).where(reports)
            )
        ).one()

        earned = [
            Money(currency=c, amount=float(a), awards=n)
            for c, a, n in await self._rows(
                select(BountyAward.currency, func.sum(_TOTAL), func.count())
                .where(awards)
                .group_by(BountyAward.currency)
                .order_by(func.sum(_TOTAL).desc())
            )
        ]
        chart_currency = earned[0].currency if earned else None
        monthly = await self._monthly(platform, chart_currency)

        return BountyAccountSummary(
            platform=platform,
            label=spec.label,
            url=spec.url,
            username=account.username if account else None,
            reputation=account.reputation if account else None,
            signal=account.signal if account else None,
            impact=account.impact if account else None,
            synced_at=account.synced_at if account else None,
            error=account.error if account else None,
            reports=totals[0],
            programs=totals[1],
            stages=stages,
            states=states,
            severities=severities,
            earned=earned,
            paid_reports=totals[4],
            first_submitted_at=totals[2],
            last_submitted_at=totals[3],
            monthly=monthly,
            chart_currency=chart_currency,
        )

    async def _monthly(self, platform: str, currency: str | None) -> list[MonthPoint]:
        """Reports submitted per month by stage, and payments per month."""
        month = func.date_trunc("month", BountyReport.submitted_at)
        points: dict[str, MonthPoint] = {}
        for m, o, r, c in await self._rows(
            select(
                month,
                func.count().filter(_in_stage(ReportStage.OPEN.value)),
                func.count().filter(_in_stage(ReportStage.RESOLVED.value)),
                func.count().filter(_in_stage(ReportStage.CLOSED.value)),
            )
            .where(
                BountyReport.platform == platform,
                col(BountyReport.submitted_at).is_not(None),
            )
            .group_by(month)
        ):
            key = m.date().isoformat()
            points[key] = MonthPoint(month=key, open=o, resolved=r, closed=c)
        if currency:
            paid_month = func.date_trunc("month", BountyAward.awarded_at)
            for m, a, n in await self._rows(
                select(paid_month, func.sum(_TOTAL), func.count())
                .where(
                    BountyAward.platform == platform,
                    BountyAward.currency == currency,
                    col(BountyAward.awarded_at).is_not(None),
                )
                .group_by(paid_month)
            ):
                key = m.date().isoformat()
                point = points.setdefault(key, MonthPoint(month=key))
                point.earned = float(a)
                point.awards = n
        if not points:
            return []
        return _fill(points)

    async def programs(self, spec: PlatformSpec) -> list[ProgramReports]:
        """Every program the account reported to, with its outcome and earnings."""
        platform = spec.key
        rows = await self._rows(
            select(
                BountyReport.program_handle,
                func.count(),
                func.count().filter(_in_stage(ReportStage.OPEN.value)),
                func.count().filter(_in_stage(ReportStage.RESOLVED.value)),
                func.count().filter(_in_stage(ReportStage.CLOSED.value)),
                func.count().filter(BountyReport.severity == "critical"),
                func.count().filter(BountyReport.severity == "high"),
                func.count().filter(_paid(platform)),
                func.min(BountyReport.submitted_at),
                func.max(BountyReport.submitted_at),
            )
            .where(
                BountyReport.platform == platform,
                col(BountyReport.program_handle).is_not(None),
            )
            .group_by(BountyReport.program_handle)
        )
        handles = {r[0] for r in rows}
        money: dict[str, list[Money]] = defaultdict(list)
        for h, c, a, n in await self._rows(
            select(
                BountyAward.program_handle,
                BountyAward.currency,
                func.sum(_TOTAL),
                func.count(),
            )
            .where(
                BountyAward.platform == platform,
                col(BountyAward.program_handle).in_(sorted(handles)),
            )
            .group_by(BountyAward.program_handle, BountyAward.currency)
        ):
            money[h].append(Money(currency=c, amount=float(a), awards=n))
        hub = await self._hub(platform, handles)
        names = await self._names(platform, handles)
        out = [
            ProgramReports(
                handle=h,
                name=names.get(h) or h,
                in_hub=h in hub,
                reports=n,
                open=o,
                resolved=r,
                closed=c,
                critical=crit,
                high=high,
                paid_reports=paid,
                earned=money.get(h, []),
                first_submitted_at=first,
                last_submitted_at=last,
            )
            for h, n, o, r, c, crit, high, paid, first, last in rows
        ]
        out.sort(
            key=lambda p: (
                -sum(m.amount for m in p.earned),
                -p.reports,
                p.name.lower(),
            )
        )
        return out

    def list_query(
        self,
        platform: str,
        *,
        states: list[str] | None = None,
        stage: str | None = None,
        programs: list[str] | None = None,
        severities: list[str] | None = None,
        paid: bool | None = None,
        q: str | None = None,
        submitted_from: datetime | None = None,
        submitted_to: datetime | None = None,
        sort: str = ReportSort.SUBMITTED.value,
        order: str = "desc",
    ) -> Select:
        query = select(BountyReport).where(BountyReport.platform == platform)
        if states:
            query = query.where(col(BountyReport.state).in_(states))
        if stage:
            query = query.where(_in_stage(stage))
        if programs:
            query = query.where(col(BountyReport.program_handle).in_(programs))
        if severities:
            query = query.where(col(BountyReport.severity).in_(severities))
        if paid is not None:
            query = query.where(_paid(platform) if paid else ~_paid(platform))
        if submitted_from:
            query = query.where(BountyReport.submitted_at >= submitted_from)
        if submitted_to:
            query = query.where(BountyReport.submitted_at < submitted_to)
        if q:
            value = q.strip()
            like = f"%{value}%"
            query = query.where(
                or_(
                    col(BountyReport.title).ilike(like),
                    col(BountyReport.external_id) == value.lstrip("#"),
                    col(BountyReport.program_handle).ilike(like),
                    col(BountyReport.weakness).ilike(like),
                    col(BountyReport.asset_identifier).ilike(like),
                )
            )
        desc = order != "asc"
        if sort == ReportSort.BOUNTY.value:
            paid_sum = (
                select(func.coalesce(func.sum(_TOTAL), 0))
                .where(
                    BountyAward.platform == platform,
                    BountyAward.report_external_id == BountyReport.external_id,
                )
                .scalar_subquery()
            )
            key = paid_sum.desc() if desc else paid_sum.asc()
        elif sort == ReportSort.SEVERITY.value:
            rank = _severity_rank()
            key = rank.asc() if desc else rank.desc()
        elif sort == ReportSort.PROGRAM.value:
            handle = col(BountyReport.program_handle)
            key = handle.desc().nulls_last() if desc else handle.asc().nulls_last()
        else:
            when = col(BountyReport.submitted_at)
            key = when.desc().nulls_last() if desc else when.asc().nulls_last()
        return query.order_by(
            key,
            col(BountyReport.submitted_at).desc().nulls_last(),
            col(BountyReport.external_id).desc(),
        )

    async def counts(self, platform: str, **filters) -> dict[str, int]:
        """Stage counts under the list's other filters."""
        base = (
            self.list_query(platform, **filters)
            .order_by(None)
            .with_only_columns(BountyReport.state, BountyReport.external_id)
            .subquery()
        )
        paid = (
            select(BountyAward.id)
            .where(
                BountyAward.platform == platform,
                BountyAward.report_external_id == base.c.external_id,
            )
            .exists()
        )
        row = (
            await self.session.execute(
                select(
                    func.count(),
                    *(
                        func.count().filter(_stage_of(base.c.state, s.value))
                        for s in ReportStage
                    ),
                    func.count().filter(paid),
                ).select_from(base)
            )
        ).one()
        return {
            "all": row[0],
            **{s.value: row[i + 1] for i, s in enumerate(ReportStage)},
            "paid": row[-1],
        }

    async def to_read(
        self, spec: PlatformSpec, rows: list[BountyReport]
    ) -> list[BountyReportRead]:
        ids = [r.external_id for r in rows]
        awards: dict[str, list[AwardRead]] = defaultdict(list)
        if ids:
            for rid, amount, bonus, currency, when in await self._rows(
                select(
                    BountyAward.report_external_id,
                    BountyAward.amount,
                    BountyAward.bonus,
                    BountyAward.currency,
                    BountyAward.awarded_at,
                )
                .where(
                    BountyAward.platform == spec.key,
                    col(BountyAward.report_external_id).in_(ids),
                )
                .order_by(col(BountyAward.awarded_at).asc().nulls_last())
            ):
                awards[rid].append(
                    AwardRead(
                        amount=float(amount),
                        bonus=float(bonus),
                        currency=currency,
                        awarded_at=when,
                    )
                )
        handles = {r.program_handle for r in rows if r.program_handle}
        names = await self._names(spec.key, handles)
        hub = await self._hub(spec.key, handles)
        return [_read(spec, r, awards.get(r.external_id, []), names, hub) for r in rows]


def _read(
    spec: PlatformSpec,
    r: BountyReport,
    awards: list[AwardRead],
    names: dict[str, str],
    hub: dict[str, str],
) -> BountyReportRead:
    state = report_state(r.state)
    summed: dict[str, list] = {}
    for a in awards:
        entry = summed.setdefault(a.currency, [0.0, 0])
        entry[0] += a.amount + a.bonus
        entry[1] += 1
    handle = r.program_handle or ""
    return BountyReportRead(
        id=r.id,
        platform=r.platform,
        external_id=r.external_id,
        url=spec.report_url.format(id=r.external_id),
        program_handle=r.program_handle,
        program_name=names.get(handle),
        program_in_hub=handle in hub,
        title=r.title,
        state=r.state,
        state_label=state.label,
        stage=state.stage.value,
        severity=r.severity,
        severity_score=r.severity_score,
        weakness=r.weakness,
        asset_type=r.asset_type,
        asset_identifier=r.asset_identifier,
        submitted_at=r.submitted_at,
        triaged_at=r.triaged_at,
        closed_at=r.closed_at,
        bounty_awarded_at=r.bounty_awarded_at,
        disclosed_at=r.disclosed_at,
        last_program_activity_at=r.last_program_activity_at,
        awarded=[
            Money(currency=c, amount=v[0], awards=v[1]) for c, v in summed.items()
        ],
        awards=awards,
    )


def _fill(points: dict[str, MonthPoint]) -> list[MonthPoint]:
    """Every month from the first to the last, gaps as zero."""
    keys = sorted(points)
    year, month = int(keys[0][:4]), int(keys[0][5:7])
    last = (int(keys[-1][:4]), int(keys[-1][5:7]))
    out = []
    while (year, month) <= last:
        key = f"{year:04d}-{month:02d}-01"
        out.append(points.get(key, MonthPoint(month=key)))
        month += 1
        if month > MONTHS:
            year, month = year + 1, 1
    return out
