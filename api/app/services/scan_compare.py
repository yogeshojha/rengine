"""Diff two runs of one target across the five result dimensions."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import (
    JSON,
    String,
    Text,
    and_,
    case,
    cast,
    false,
    func,
    literal,
    not_,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.asset_query import NO_JIT, vuln_suppressed
from app.services.surface_scope import covering_stages
from shared.definitions.compare import (
    AUTH_STATUS,
    COMPARE_KEYS,
    DEFAULT_RANK,
    DIFF_FIELD_INDENT,
    DIFF_MARK,
    DIFF_PAGE,
    INTEL_FIELDS,
    LISTED_VERBS,
    MAX_COMPARABLE_RUNS,
    MAX_DIFF_LINES,
    MAX_RUN_DIFFERENCES,
    OK_MAX,
    OK_MIN,
    REFUSAL_REASON,
    RUN_FACETS,
    SIGNAL_RANK,
    WATCHED_FIELDS,
    ChangeSignal,
    ChangeVerb,
    Comparability,
    FacetKind,
    FieldKind,
    Refusal,
    Tone,
)
from shared.definitions.ports import SENSITIVE_PORTS
from shared.definitions.surface import (
    SURFACE_LABELS,
    SURFACE_NOUN,
    SURFACE_ORDER,
    SurfaceDimension,
)
from shared.definitions.vulnerabilities import SEVERITY_ORDER, Severity
from shared.enums.scan import (
    SCAN_LIVE_STATUSES,
    ScanActivityStatus,
    ScanScope,
    ScanStatus,
)
from shared.models.compare import (
    ChangeField,
    ChangeRow,
    ChangeRows,
    ComparableRun,
    CoverageLine,
    DimensionDelta,
    DimensionVerdict,
    RunDifference,
    RunSide,
    ScanComparison,
    ScreenshotPair,
    SettingDiff,
    StageDiff,
)
from shared.models.endpoint import Endpoint, EndpointCoverage
from shared.models.ip_address import IpAddress
from shared.models.port import Port
from shared.models.scan import Scan
from shared.models.scan_activity import ScanActivity
from shared.models.software import SoftwareCve
from shared.models.subdomain import Subdomain
from shared.models.target import Target
from shared.models.vulnerability import Vulnerability, VulnerabilityCoverage
from shared.utils.datetime import utc_now
from stages.registry import stage_by_name

RAN = (ScanActivityStatus.SUCCESS.value, ScanActivityStatus.PARTIAL.value)
CLEAN = ScanActivityStatus.SUCCESS.value
SIGNAL_BY_RANK: dict[int, str] = {v: k for k, v in SIGNAL_RANK.items()}
SENSITIVE = tuple(SENSITIVE_PORTS)
LIST_PREVIEW = 4
COVERAGE_TOLERANCE = 0.2


@dataclass(frozen=True)
class DimSpec:
    dimension: str
    model: Any
    keys: tuple[str, ...]
    title: str
    subtitle: tuple[str, ...]
    display: tuple[str, ...]


SPECS: dict[str, DimSpec] = {
    SurfaceDimension.WEB_ASSETS.value: DimSpec(
        dimension=SurfaceDimension.WEB_ASSETS.value,
        model=Subdomain,
        keys=COMPARE_KEYS[SurfaceDimension.WEB_ASSETS.value],
        title="name",
        subtitle=("page_title",),
        display=("http_status", "interest_band", "screenshot_path", "is_active"),
    ),
    SurfaceDimension.ENDPOINTS.value: DimSpec(
        dimension=SurfaceDimension.ENDPOINTS.value,
        model=Endpoint,
        keys=COMPARE_KEYS[SurfaceDimension.ENDPOINTS.value],
        title="url",
        subtitle=("host",),
        display=("status_code", "param_count", "endpoint_class"),
    ),
    SurfaceDimension.SERVICES.value: DimSpec(
        dimension=SurfaceDimension.SERVICES.value,
        model=Port,
        keys=COMPARE_KEYS[SurfaceDimension.SERVICES.value],
        title="ip",
        subtitle=("service_name",),
        display=("number", "service_class", "is_http"),
    ),
    SurfaceDimension.IPS.value: DimSpec(
        dimension=SurfaceDimension.IPS.value,
        model=IpAddress,
        keys=COMPARE_KEYS[SurfaceDimension.IPS.value],
        title="ip",
        subtitle=("asn_org",),
        display=("country", "is_cdn", "is_alive", "asn"),
    ),
    SurfaceDimension.VULNERABILITIES.value: DimSpec(
        dimension=SurfaceDimension.VULNERABILITIES.value,
        model=Vulnerability,
        keys=COMPARE_KEYS[SurfaceDimension.VULNERABILITIES.value],
        title="template_name",
        subtitle=("matched_at",),
        display=("template_id", "severity", "is_kev", "host", "exploit_score"),
    ),
    SurfaceDimension.SOFTWARE.value: DimSpec(
        dimension=SurfaceDimension.SOFTWARE.value,
        model=SoftwareCve,
        keys=COMPARE_KEYS[SurfaceDimension.SOFTWARE.value],
        title="cve",
        subtitle=("host",),
        display=("name", "version", "severity", "confidence", "is_kev"),
    ),
}


# ---------- value rendering ----------


def _text_value(value) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, datetime):
        return value.strftime("%d %b %Y %H:%M")
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value) or None
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in sorted(value.items())) or None
    return str(value)


def _setting_equal(left, right) -> bool:
    if isinstance(left, list) and isinstance(right, list):
        return sorted(map(str, left)) == sorted(map(str, right))
    return left == right


def _list_delta(before, after) -> tuple[str | None, str | None, str]:
    old = {str(v) for v in (before or [])}
    new = {str(v) for v in (after or [])}
    gained = sorted(new - old)
    lost = sorted(old - new)
    if not gained and not lost:
        return None, None, Tone.NEUTRAL.value
    parts = []
    if gained:
        parts.append(f"+{', '.join(gained[:LIST_PREVIEW])}")
        if len(gained) > LIST_PREVIEW:
            parts.append(f"+{len(gained) - LIST_PREVIEW} more")
    if lost:
        parts.append(f"-{', '.join(lost[:LIST_PREVIEW])}")
        if len(lost) > LIST_PREVIEW:
            parts.append(f"-{len(lost) - LIST_PREVIEW} more")
    tone = (
        Tone.UP.value
        if gained and not lost
        else Tone.DOWN.value
        if lost and not gained
        else Tone.NEUTRAL.value
    )
    return None, " · ".join(parts), tone


def _started_at(scan: Scan) -> datetime | None:
    return scan.started_at or scan.created_at


def _dig(config: dict, path: str):
    value = config
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _facet_value(facet, config: dict) -> str | None:
    raw = _dig(config, facet.path)
    if facet.kind == FacetKind.MASKED.value:
        return "set" if raw else "none"
    if facet.kind == FacetKind.COUNT.value:
        return str(len(raw or {})) if isinstance(raw, dict) else str(len(raw or []))
    if facet.kind == FacetKind.LIST.value:
        items = sorted(str(v) for v in (raw or []))
        return ", ".join(items) if items else None
    if facet.kind == FacetKind.BOOL.value:
        return None if raw is None else ("yes" if raw else "no")
    return _text_value(raw)


# ---------- column helpers ----------


def _columns(spec: DimSpec) -> tuple[str, ...]:
    names: list[str] = []
    for group in (
        spec.keys,
        tuple(f.name for f in WATCHED_FIELDS[spec.dimension]),
        (spec.title,),
        spec.subtitle,
        spec.display,
    ):
        for name in group:
            if name not in names and hasattr(spec.model, name):
                names.append(name)
    if spec.dimension == SurfaceDimension.VULNERABILITIES.value:
        names.extend(f for f in INTEL_FIELDS if f not in names)
    return tuple(names)


def _side(spec: DimSpec, scan_id: UUID, columns: tuple[str, ...]):
    model = spec.model
    query = select(*[getattr(model, name) for name in columns]).where(
        model.scan_id == scan_id
    )
    if spec.dimension == SurfaceDimension.VULNERABILITIES.value:
        query = query.where(not_(vuln_suppressed(scan_id)))
    return query.subquery()


def _is_text(column) -> bool:
    """Whether the column holds text."""
    affinity = getattr(column.type, "_type_affinity", None)
    return bool(affinity) and issubclass(affinity, String)


def _blank(value):
    """Read empty text as NULL."""
    return func.nullif(value, "") if _is_text(value) else value


def _same_value(old, new) -> bool:
    """Whether two values match, with empty text read as NULL."""
    left = None if old == "" else old
    right = None if new == "" else new
    return left == right


def _differs(a, b, names: list[str]):
    parts = []
    for name in names:
        ca, cb = a.c[name], b.c[name]
        if isinstance(ca.type, JSON):
            ja, jb = cast(ca, JSONB), cast(cb, JSONB)
            same = and_(ja.contains(jb), jb.contains(ja))
            both_null = and_(ca.is_(None), cb.is_(None))
            parts.append(not_(or_(both_null, func.coalesce(same, false()))))
        else:
            parts.append(_blank(ca).is_distinct_from(_blank(cb)))
    return or_(*parts) if parts else false()


def _watched_names(spec: DimSpec) -> list[str]:
    return [
        f.name for f in WATCHED_FIELDS[spec.dimension] if hasattr(spec.model, f.name)
    ]


def _severity_case(column):
    return case(
        *[(column == name, literal(i)) for i, name in enumerate(SEVERITY_ORDER)],
        else_=literal(len(SEVERITY_ORDER)),
    )


def _live_status(column):
    return and_(column.isnot(None), column >= OK_MIN, column < OK_MAX)


def _rules(spec: DimSpec, a, b, appeared, gone, both):
    d = spec.dimension
    if d == SurfaceDimension.VULNERABILITIES.value:
        return (
            (ChangeSignal.KEV_APPEARED, and_(appeared, b.c.is_kev.is_(True))),
            (
                ChangeSignal.CRITICAL_APPEARED,
                and_(
                    appeared,
                    b.c.severity.in_((Severity.CRITICAL.value, Severity.HIGH.value)),
                ),
            ),
            (ChangeSignal.FINDING_APPEARED, appeared),
            (
                ChangeSignal.SEVERITY_RAISED,
                and_(
                    both,
                    _severity_case(b.c.severity) < _severity_case(a.c.severity),
                ),
            ),
            (ChangeSignal.ATTRIBUTES_CHANGED, both),
            (ChangeSignal.FINDING_GONE, gone),
        )
    if d == SurfaceDimension.SERVICES.value:
        return (
            (
                ChangeSignal.SENSITIVE_SERVICE_OPENED,
                and_(appeared, b.c.number.in_(SENSITIVE)),
            ),
            (ChangeSignal.SERVICE_OPENED, appeared),
            (ChangeSignal.ATTRIBUTES_CHANGED, both),
            (ChangeSignal.SERVICE_CLOSED, gone),
        )
    if d == SurfaceDimension.IPS.value:
        return (
            (
                ChangeSignal.HOSTING_MOVED,
                and_(
                    both,
                    or_(
                        a.c.asn.is_distinct_from(b.c.asn),
                        a.c.country.is_distinct_from(b.c.country),
                    ),
                ),
            ),
            (ChangeSignal.ADDRESS_APPEARED, appeared),
            (ChangeSignal.ATTRIBUTES_CHANGED, both),
            (ChangeSignal.ASSET_GONE, gone),
        )
    if d == SurfaceDimension.ENDPOINTS.value:
        return (
            (
                ChangeSignal.AUTH_DROPPED,
                and_(
                    both,
                    a.c.status_code.in_(AUTH_STATUS),
                    _live_status(b.c.status_code),
                ),
            ),
            (
                ChangeSignal.BODY_CHANGED,
                and_(
                    both,
                    a.c.content_hash.is_distinct_from(b.c.content_hash),
                    b.c.param_count > 0,
                ),
            ),
            (ChangeSignal.ENDPOINT_APPEARED, appeared),
            (ChangeSignal.ATTRIBUTES_CHANGED, both),
            (ChangeSignal.ASSET_GONE, gone),
        )
    return (
        (
            ChangeSignal.AUTH_DROPPED,
            and_(both, a.c.http_status.in_(AUTH_STATUS), _live_status(b.c.http_status)),
        ),
        (
            ChangeSignal.CERT_EXPIRED,
            and_(both, b.c.tls_expired.is_(True), a.c.tls_expired.isnot(True)),
        ),
        (
            ChangeSignal.WAF_GONE,
            and_(both, a.c.waf.isnot(None), b.c.waf.is_(None)),
        ),
        (
            ChangeSignal.EXPOSED_HOST_APPEARED,
            and_(appeared, b.c.interest_band.isnot(None)),
        ),
        (
            ChangeSignal.HOST_WOKE,
            and_(both, a.c.is_active.is_(False), b.c.is_active.is_(True)),
        ),
        (
            ChangeSignal.CDN_GONE,
            and_(both, a.c.cdn_name.isnot(None), b.c.cdn_name.is_(None)),
        ),
        (ChangeSignal.HOST_APPEARED, appeared),
        (ChangeSignal.ATTRIBUTES_CHANGED, both),
        (ChangeSignal.HOST_GONE, gone),
    )


@lru_cache(maxsize=1)
def _stage_titles() -> dict[str, str]:
    return {name: spec.title for name, spec in stage_by_name().items()}


@lru_cache(maxsize=1)
def _stage_field_labels() -> dict[str, dict[str, str]]:
    """Stage, then field, then the field's label."""
    out: dict[str, dict[str, str]] = {}
    for name, spec in stage_by_name().items():
        props = spec.schema.get("properties") or {}
        out[name] = {key: (value.get("title") or key) for key, value in props.items()}
    return out


class ScanCompareService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ---------- entry points ----------

    async def comparison(
        self, baseline_id: UUID | None, current_id: UUID, project_id: UUID
    ) -> ScanComparison:
        baseline, current = await self._pair(baseline_id, current_id, project_id)
        target = await self.session.get(Target, current.target_id)
        activities = await self._activities([baseline.id, current.id])
        titles = _stage_titles()

        setting_diff, identical = self._setting_diff(baseline, current, titles)

        await self.session.execute(text(NO_JIT))
        deltas: list[DimensionDelta] = []
        for dimension in SURFACE_ORDER:
            deltas.append(
                await self._delta(
                    dimension, baseline, current, activities, setting_diff
                )
            )

        stage_diff = self._stage_diff(baseline, current, activities, titles)
        run_diff = self._run_diff(baseline, current)
        between = await self._runs_between(baseline, current)
        worst = self._overall(deltas, setting_diff, run_diff, baseline, current)
        suggestion = None
        if worst != Comparability.LIKE_FOR_LIKE.value:
            suggestion = await self._suggestion(baseline, current, titles)
        total = sum(d.listed for d in deltas)

        return ScanComparison(
            target_id=current.target_id,
            target_value=target.target_value if target else "",
            target_type=target.target_type if target else "",
            baseline=self._side_read(baseline, activities, deltas, "total_baseline"),
            current=self._side_read(current, activities, deltas, "total_current"),
            dimensions=deltas,
            stage_diff=stage_diff,
            setting_diff=setting_diff,
            settings_identical=identical,
            run_diff=run_diff,
            runs_between=between,
            comparability=worst,
            headline=self._headline(total, deltas, current),
            summary=self._summary(deltas, setting_diff, run_diff),
            changes_total=total,
            live=current.status in SCAN_LIVE_STATUSES,
            suggestion=suggestion,
            generated_at=utc_now(),
        )

    async def rows(
        self,
        baseline_id: UUID | None,
        current_id: UUID,
        project_id: UUID,
        dimension: str,
        verbs: list[str],
        page: int,
        size: int,
    ) -> ChangeRows:
        if dimension not in SPECS:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown dimension '{dimension}'.",
            )
        baseline, current = await self._pair(baseline_id, current_id, project_id)
        activities = await self._activities([baseline.id, current.id])
        confirmed = self._confirmed(dimension, current, activities)
        wanted = self._wanted(verbs, confirmed)
        spec = SPECS[dimension]

        if not wanted:
            return ChangeRows(dimension=dimension, page=page, size=size)

        await self.session.execute(text(NO_JIT))
        columns = _columns(spec)
        a = _side(spec, baseline.id, columns)
        b = _side(spec, current.id, columns)
        joined, appeared, gone, both = self._join(spec, a, b)
        changed = and_(both, _differs(a, b, _watched_names(spec)))
        unchanged = and_(both, not_(_differs(a, b, _watched_names(spec))))

        clauses = []
        if ChangeVerb.APPEARED.value in wanted:
            clauses.append(appeared)
        if ChangeVerb.CHANGED.value in wanted:
            clauses.append(changed)
        if {ChangeVerb.DISAPPEARED.value, ChangeVerb.UNCONFIRMED.value} & wanted:
            clauses.append(gone)
        if ChangeVerb.UNCHANGED.value in wanted:
            clauses.append(unchanged)
        where = or_(*clauses)

        rank = case(
            *[
                (pred, literal(SIGNAL_RANK[sig.value]))
                for sig, pred in _rules(spec, a, b, appeared, gone, both)
            ],
            else_=literal(DEFAULT_RANK),
        ).label("rank")

        total = await self.session.scalar(
            select(func.count()).select_from(joined).where(where)
        )
        order_keys = [
            func.coalesce(cast(b.c[key], Text), cast(a.c[key], Text))
            for key in spec.keys
        ]
        result = await self.session.execute(
            select(
                rank,
                appeared.label("is_appeared"),
                gone.label("is_gone"),
                *[a.c[name].label(f"a_{name}") for name in columns],
                *[b.c[name].label(f"b_{name}") for name in columns],
            )
            .select_from(joined)
            .where(where)
            .order_by(rank.asc(), *[key.asc() for key in order_keys])
            .offset((page - 1) * size)
            .limit(size)
        )

        items = [
            self._row(spec, row._mapping, columns, confirmed, baseline.id, current.id)
            for row in result.all()
        ]
        return ChangeRows(
            dimension=dimension,
            items=items,
            total=int(total or 0),
            page=page,
            size=size,
        )

    async def diff(
        self,
        baseline_id: UUID | None,
        current_id: UUID,
        project_id: UUID,
        dimension: str | None,
        verbs: list[str],
    ) -> str:
        """The comparison as a unified diff."""
        report = await self.comparison(baseline_id, current_id, project_id)
        wanted = [
            d
            for d in report.dimensions
            if dimension is None or d.dimension == dimension
        ]
        lines = self._diff_head(report, wanted)

        for delta in wanted:
            if delta.verdict.comparability == Comparability.NOT_COVERED.value:
                if delta.verdict.compared:
                    lines.append(f"# {delta.dimension}  {delta.verdict.note.lower()}")
                continue
            if not delta.listed:
                continue
            lines.append("")
            tally = f"+{delta.appeared:,} ~{delta.changed:,} -{delta.disappeared:,}"
            if delta.unconfirmed:
                tally += f" ?{delta.unconfirmed:,}"
            lines.append(
                f"@@ {delta.dimension}  "
                f"{delta.total_baseline:,} → {delta.total_current:,}  {tally} @@"
            )
            lines.extend(
                await self._diff_rows(
                    report, project_id, delta, verbs, MAX_DIFF_LINES - len(lines)
                )
            )
            if len(lines) >= MAX_DIFF_LINES:
                lines.append(f"# truncated at {MAX_DIFF_LINES:,} lines")
                break

        return "\n".join(lines) + "\n"

    def _diff_head(
        self, report: ScanComparison, wanted: list[DimensionDelta]
    ) -> list[str]:
        def side(run: RunSide) -> str:
            when = run.started_at.strftime("%d %b %Y %H:%M") if run.started_at else "—"
            rows = sum(run.counts.values())
            return f"{run.engine_name}  {when}  {rows:,} rows"

        lines = [
            f"--- {side(report.baseline)}",
            f"+++ {side(report.current)}",
            f"# {report.target_value}",
            f"# {report.comparability.replace('_', ' ')} · {report.summary}",
        ]
        lines.extend(
            f"# run · {row.label}  {row.baseline or 'none'} → {row.current or 'none'}"
            for row in report.run_diff
            if row.material
        )
        if report.runs_between:
            lines.append(f"# {report.runs_between} run(s) ran between these two")
        tally = " · ".join(
            f"{d.dimension} {d.total_baseline:,}→{d.total_current:,} "
            f"+{d.appeared:,}~{d.changed:,}-{d.disappeared + d.unconfirmed:,}"
            for d in wanted
            if d.verdict.compared
        )
        if tally:
            lines.append(f"# {tally}")
        return lines

    async def _diff_rows(
        self,
        report: ScanComparison,
        project_id: UUID,
        delta: DimensionDelta,
        verbs: list[str],
        budget: int,
    ) -> list[str]:
        lines: list[str] = []
        page = 1
        while len(lines) < budget:
            result = await self.rows(
                baseline_id=report.baseline.scan_id,
                current_id=report.current.scan_id,
                project_id=project_id,
                dimension=delta.dimension,
                verbs=verbs,
                page=page,
                size=DIFF_PAGE,
            )
            if not result.items:
                break
            for row in result.items:
                lines.append(f"{DIFF_MARK.get(row.verb, ' ')} {self._diff_label(row)}")
                lines.extend(
                    f"{DIFF_FIELD_INDENT}{field.label:<16}{self._diff_field(field)}"
                    for field in row.fields
                )
                if len(lines) >= budget:
                    return lines[:budget]
            if page * DIFF_PAGE >= result.total:
                break
            page += 1
        return lines

    def _diff_label(self, row: ChangeRow) -> str:
        parts = [f"[{row.severity}]" if row.severity else "", row.title, row.subtitle]
        return "  ".join(part for part in parts if part)

    def _diff_field(self, field: ChangeField) -> str:
        if field.before is None:
            return field.after or "gone"
        return f"{field.before} → {field.after or 'none'}"

    async def comparable(self, scan_id: UUID, project_id: UUID) -> list[ComparableRun]:
        scan = await self._scan(scan_id, project_id)
        result = await self.session.execute(
            select(Scan)
            .where(
                Scan.target_id == scan.target_id,
                Scan.project_id == project_id,
                Scan.id != scan.id,
            )
            .order_by(func.coalesce(Scan.started_at, Scan.created_at).desc())
            .limit(MAX_COMPARABLE_RUNS)
        )
        runs = list(result.scalars().all())
        activities = await self._activities([r.id for r in runs])
        census = scan.scope == ScanScope.FULL.value

        return [
            self._comparable_read(run, activities, self._refusal(scan, run, census))
            for run in runs
        ]

    # ---------- pair resolution ----------

    async def _scan(self, scan_id: UUID, project_id: UUID) -> Scan:
        scan = await self.session.get(Scan, scan_id)
        if scan is None or scan.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found."
            )
        return scan

    async def _pair(
        self, baseline_id: UUID | None, current_id: UUID, project_id: UUID
    ) -> tuple[Scan, Scan]:
        current = await self._scan(current_id, project_id)
        if baseline_id is None:
            baseline_id = await self._previous(current, project_id)
        if baseline_id == current_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=REFUSAL_REASON[Refusal.SAME_RUN.value],
            )
        baseline = await self._scan(baseline_id, project_id)
        current = await self._scan(current_id, project_id)
        refusal = self._refusal(
            current, baseline, current.scope == ScanScope.FULL.value
        )
        if refusal:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=refusal
            )
        return baseline, current

    async def _previous(self, current: Scan, project_id: UUID) -> UUID:
        """The newest earlier run of the same scope."""
        started = func.coalesce(Scan.started_at, Scan.created_at)
        result = await self.session.execute(
            select(Scan)
            .where(
                Scan.target_id == current.target_id,
                Scan.project_id == project_id,
                Scan.id != current.id,
                Scan.scope == current.scope,
                Scan.status.not_in(SCAN_LIVE_STATUSES),
                started < func.coalesce(current.started_at, current.created_at),
            )
            .order_by(started.desc())
            .limit(1)
        )
        scan = result.scalars().first()
        if scan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REFUSAL_REASON[Refusal.NO_EARLIER_RUN.value],
            )
        return scan.id

    def _refusal(self, scan: Scan, other: Scan, census: bool) -> str:
        if other.target_id != scan.target_id:
            return REFUSAL_REASON[Refusal.DIFFERENT_TARGET.value]
        if other.status in SCAN_LIVE_STATUSES:
            return REFUSAL_REASON[Refusal.UNFINISHED.value]
        if census and other.scope != ScanScope.FULL.value:
            return REFUSAL_REASON[Refusal.FOCUSED_AGAINST_FULL.value]
        if not census and other.scope == ScanScope.FULL.value:
            return REFUSAL_REASON[Refusal.FULL_AGAINST_FOCUSED.value]
        return ""

    # ---------- per-dimension delta ----------

    async def _delta(
        self,
        dimension: str,
        baseline: Scan,
        current: Scan,
        activities: dict[UUID, dict[str, str]],
        settings: list[SettingDiff],
    ) -> DimensionDelta:
        spec = SPECS[dimension]
        noun, noun_plural = SURFACE_NOUN[dimension]
        columns = _columns(spec)
        a = _side(spec, baseline.id, columns)
        b = _side(spec, current.id, columns)
        joined, appeared, gone, both = self._join(spec, a, b)
        watched = _watched_names(spec)
        differs = _differs(a, b, watched)

        intel = false()
        if dimension == SurfaceDimension.VULNERABILITIES.value:
            names = [f for f in INTEL_FIELDS if hasattr(spec.model, f)]
            intel = _differs(a, b, names)

        row = (
            await self.session.execute(
                select(
                    func.count().filter(appeared),
                    func.count().filter(gone),
                    func.count().filter(and_(both, differs)),
                    func.count().filter(and_(both, not_(differs))),
                    func.count().filter(and_(both, not_(differs), intel)),
                ).select_from(joined)
            )
        ).one()

        appeared_n, gone_n, changed_n, unchanged_n, intel_n = (int(v or 0) for v in row)
        rows_baseline = changed_n + unchanged_n + gone_n
        rows_current = changed_n + unchanged_n + appeared_n
        verdict = await self._verdict(
            dimension,
            baseline,
            current,
            activities,
            settings,
            gone_n,
            rows_baseline,
            rows_current,
        )
        delta = DimensionDelta(
            dimension=dimension,
            label=SURFACE_LABELS[dimension],
            noun=noun,
            noun_plural=noun_plural,
            verdict=verdict,
            total_baseline=changed_n + unchanged_n + gone_n,
            total_current=changed_n + unchanged_n + appeared_n,
            appeared=appeared_n,
            changed=changed_n,
            unchanged=unchanged_n,
            intel_moved=intel_n,
        )
        if verdict.confirmed:
            delta.disappeared = gone_n
        else:
            delta.unconfirmed = gone_n
        if verdict.comparability == Comparability.NOT_COVERED.value:
            delta.appeared = 0
            delta.changed = 0
            delta.disappeared = 0
            delta.unconfirmed = 0
        return delta

    def _join(self, spec: DimSpec, a, b):
        on = and_(*[a.c[k] == b.c[k] for k in spec.keys])
        joined = a.join(b, on, full=True)
        first = spec.keys[0]
        appeared = a.c[first].is_(None)
        gone = b.c[first].is_(None)
        both = and_(a.c[first].isnot(None), b.c[first].isnot(None))
        return joined, appeared, gone, both

    # ---------- comparability ----------

    async def _activities(self, ids: list[UUID]) -> dict[UUID, dict[str, str]]:
        if not ids:
            return {}
        result = await self.session.execute(
            select(ScanActivity.scan_id, ScanActivity.name, ScanActivity.status).where(
                ScanActivity.scan_id.in_(ids)
            )
        )
        out: dict[UUID, dict[str, str]] = defaultdict(dict)
        for scan_id, name, state in result.all():
            out[scan_id][name] = state
        return out

    def _ran(
        self, dimension: str, scan: Scan, activities: dict[UUID, dict[str, str]]
    ) -> bool:
        names = covering_stages()[dimension]
        ran = activities.get(scan.id, {})
        return any(ran.get(name) in RAN for name in names)

    def _clean(
        self, dimension: str, scan: Scan, activities: dict[UUID, dict[str, str]]
    ) -> bool:
        names = covering_stages()[dimension]
        ran = activities.get(scan.id, {})
        return any(ran.get(name) == CLEAN for name in names)

    def _confirmed(
        self, dimension: str, current: Scan, activities: dict[UUID, dict[str, str]]
    ) -> bool:
        return self._clean(dimension, current, activities)

    async def _verdict(
        self,
        dimension: str,
        baseline: Scan,
        current: Scan,
        activities: dict[UUID, dict[str, str]],
        settings: list[SettingDiff],
        gone: int,
        rows_baseline: int,
        rows_current: int,
    ) -> DimensionVerdict:
        # measured rows, not the rollup columns
        covered_a = self._ran(dimension, baseline, activities) or rows_baseline > 0
        covered_b = self._ran(dimension, current, activities) or rows_current > 0
        verdict = DimensionVerdict(
            dimension=dimension,
            covered_baseline=bool(covered_a),
            covered_current=bool(covered_b),
            compared=bool(covered_a or covered_b),
            confirmed=self._clean(dimension, current, activities),
        )
        if not covered_a or not covered_b:
            verdict.comparability = Comparability.NOT_COVERED.value
            verdict.stages = sorted(covering_stages()[dimension])
            if not verdict.compared:
                verdict.note = "Neither run scanned this."
            else:
                side = "earlier" if not covered_a else "later"
                verdict.note = f"Not scanned in the {side} run."
            return verdict

        verdict.coverage = await self._coverage_lines(dimension, baseline, current)
        verdict.settings = self._dimension_settings(dimension, settings)
        if verdict.settings:
            verdict.comparability = Comparability.SETTINGS_DIFFER.value
            verdict.stages = sorted({row.stage for row in verdict.settings})
            names = ", ".join(sorted({row.title for row in verdict.settings}))
            verdict.note = f"{names} ran with different settings."
            return verdict

        if not verdict.confirmed:
            noun, noun_plural = SURFACE_NOUN[dimension]
            missing = noun if gone == 1 else noun_plural
            verdict.comparability = Comparability.QUALITY_DIFFERS.value
            verdict.note = (
                f"The later run did not finish this dimension cleanly. "
                f"{gone:,} missing {missing} cannot be confirmed."
            )
            return verdict

        if verdict.coverage:
            verdict.comparability = Comparability.QUALITY_DIFFERS.value
            measured = ", ".join(line.label.lower() for line in verdict.coverage)
            verdict.note = f"The runs differ in {measured}."
        return verdict

    async def _coverage_lines(
        self, dimension: str, baseline: Scan, current: Scan
    ) -> list[CoverageLine]:
        if dimension == SurfaceDimension.VULNERABILITIES.value:
            return await self._vuln_coverage(baseline.id, current.id)
        if dimension == SurfaceDimension.ENDPOINTS.value:
            return await self._endpoint_coverage(baseline.id, current.id)
        return []

    async def _vuln_coverage(self, a_id: UUID, b_id: UUID) -> list[CoverageLine]:
        result = await self.session.execute(
            select(
                VulnerabilityCoverage.scan_id,
                func.sum(VulnerabilityCoverage.requests_sent),
                func.sum(VulnerabilityCoverage.hosts_scanned),
                func.sum(VulnerabilityCoverage.templates_loaded),
            )
            .where(VulnerabilityCoverage.scan_id.in_([a_id, b_id]))
            .group_by(VulnerabilityCoverage.scan_id)
        )
        rows = {r[0]: r[1:] for r in result.all()}
        return self._coverage_diff(
            rows.get(a_id),
            rows.get(b_id),
            (("Requests sent", 0), ("Hosts scanned", 1), ("Checks loaded", 2)),
        )

    async def _endpoint_coverage(self, a_id: UUID, b_id: UUID) -> list[CoverageLine]:
        result = await self.session.execute(
            select(
                EndpointCoverage.scan_id,
                func.sum(EndpointCoverage.urls_found),
                func.sum(EndpointCoverage.pages_fetched),
                func.sum(EndpointCoverage.hosts_scanned),
            )
            .where(EndpointCoverage.scan_id.in_([a_id, b_id]))
            .group_by(EndpointCoverage.scan_id)
        )
        rows = {r[0]: r[1:] for r in result.all()}
        return self._coverage_diff(
            rows.get(a_id),
            rows.get(b_id),
            (("URLs found", 0), ("Pages fetched", 1), ("Hosts", 2)),
        )

    def _coverage_diff(self, left, right, fields) -> list[CoverageLine]:
        if left is None or right is None:
            return []
        out: list[CoverageLine] = []
        for label, index in fields:
            a, b = left[index], right[index]
            if a is None or b is None or a == b:
                continue
            if min(a, b) and abs(a - b) / max(a, b) < COVERAGE_TOLERANCE:
                continue
            out.append(
                CoverageLine(label=label, baseline=f"{int(a):,}", current=f"{int(b):,}")
            )
        return out

    def _dimension_settings(
        self, dimension: str, settings: list[SettingDiff]
    ) -> list[SettingDiff]:
        names = covering_stages()[dimension]
        return [row for row in settings if row.stage in names]

    def _run_diff(self, baseline: Scan, current: Scan) -> list[RunDifference]:
        """How the two runs themselves were set up differently."""
        left = baseline.execution_config or {}
        right = current.execution_config or {}
        out: list[RunDifference] = []

        for key, label, a, b in (
            ("engine", "Engine", baseline.engine_name, current.engine_name),
            (
                "context",
                "Scan context",
                baseline.context_name or "engine defaults",
                current.context_name or "engine defaults",
            ),
            (
                "schedule",
                "Started by",
                baseline.schedule_type or "manual",
                current.schedule_type or "manual",
            ),
        ):
            if a != b:
                out.append(
                    RunDifference(
                        key=key,
                        label=label,
                        baseline=a,
                        current=b,
                        material=key != "schedule",
                    )
                )

        for facet in RUN_FACETS:
            a = _facet_value(facet, left)
            b = _facet_value(facet, right)
            if a == b:
                continue
            out.append(
                RunDifference(
                    key=facet.key,
                    label=facet.label,
                    baseline=a,
                    current=b,
                    material=facet.material,
                )
            )
        return out[:MAX_RUN_DIFFERENCES]

    async def _runs_between(self, baseline: Scan, current: Scan) -> int:
        """Census runs of this target that ran between the two."""
        started = func.coalesce(Scan.started_at, Scan.created_at)
        low = _started_at(baseline)
        high = _started_at(current)
        if low is None or high is None:
            return 0
        if low > high:
            low, high = high, low
        counted = await self.session.scalar(
            select(func.count())
            .select_from(Scan)
            .where(
                Scan.target_id == current.target_id,
                Scan.scope == current.scope,
                Scan.id.not_in([baseline.id, current.id]),
                Scan.status.not_in(SCAN_LIVE_STATUSES),
                started > low,
                started < high,
            )
        )
        return int(counted or 0)

    async def _suggestion(
        self,
        baseline: Scan,
        current: Scan,
        titles: dict[str, str],
    ) -> ComparableRun | None:
        """The nearest earlier run that would compare like for like."""
        started = func.coalesce(Scan.started_at, Scan.created_at)
        cutoff = _started_at(current)
        if cutoff is None:
            return None
        rows = await self.session.execute(
            select(Scan)
            .where(
                Scan.target_id == current.target_id,
                Scan.project_id == current.project_id,
                Scan.scope == current.scope,
                Scan.id.not_in([baseline.id, current.id]),
                Scan.status == ScanStatus.COMPLETED.value,
                started < cutoff,
            )
            .order_by(started.desc())
            .limit(MAX_COMPARABLE_RUNS)
        )
        for row in rows.scalars().all():
            if self._run_diff(row, current):
                continue
            if self._setting_diff(row, current, titles)[0]:
                continue
            ran = await self._activities([row.id])
            return self._comparable_read(row, ran, "")
        return None

    def _stage_diff(
        self,
        baseline: Scan,
        current: Scan,
        activities: dict[UUID, dict[str, str]],
        titles: dict[str, str],
    ) -> list[StageDiff]:
        left = activities.get(baseline.id, {})
        right = activities.get(current.id, {})
        out = []
        for name in sorted(set(left) | set(right)):
            if left.get(name) == right.get(name):
                continue
            out.append(
                StageDiff(
                    name=name,
                    title=titles.get(name, name),
                    baseline=left.get(name),
                    current=right.get(name),
                )
            )
        return out

    def _setting_diff(
        self, baseline: Scan, current: Scan, titles: dict[str, str]
    ) -> tuple[list[SettingDiff], int]:
        left = (baseline.execution_config or {}).get("stages") or {}
        right = (current.execution_config or {}).get("stages") or {}
        by_stage = _stage_field_labels()
        out: list[SettingDiff] = []
        identical = 0
        for name in sorted(set(left) | set(right)):
            before = left.get(name) or {}
            after = right.get(name) or {}
            fields = sorted(set(before) | set(after))
            labels = by_stage.get(name, {})
            for field in fields:
                if _setting_equal(before.get(field), after.get(field)):
                    identical += 1
                    continue
                out.append(
                    SettingDiff(
                        stage=name,
                        title=titles.get(name, name),
                        field=field,
                        label=labels.get(field, field),
                        before=_text_value(before.get(field)),
                        after=_text_value(after.get(field)),
                    )
                )
        return out, identical

    def _overall(
        self,
        deltas: list[DimensionDelta],
        settings: list[SettingDiff],
        run_diff: list[RunDifference],
        baseline: Scan,
        current: Scan,
    ) -> str:
        order = (
            Comparability.NOT_COVERED.value,
            Comparability.SETTINGS_DIFFER.value,
            Comparability.QUALITY_DIFFERS.value,
            Comparability.LIKE_FOR_LIKE.value,
        )
        found = {d.verdict.comparability for d in deltas if d.verdict.compared}
        if settings or any(row.material for row in run_diff):
            found.add(Comparability.SETTINGS_DIFFER.value)
        if any(
            run.status != ScanStatus.COMPLETED.value
            and run.status not in SCAN_LIVE_STATUSES
            for run in (baseline, current)
        ):
            found.add(Comparability.QUALITY_DIFFERS.value)
        for key in order:
            if key in found:
                return key
        return Comparability.LIKE_FOR_LIKE.value

    # ---------- narration ----------

    def _headline(self, total: int, deltas: list[DimensionDelta], current: Scan) -> str:
        if current.status in SCAN_LIVE_STATUSES:
            return "Scan in progress"
        if total == 0:
            return "Nothing changed"
        top = max(deltas, key=lambda d: d.listed)
        noun = top.noun if top.listed == 1 else top.noun_plural
        if total == top.listed:
            return f"{total:,} {noun} changed"
        return (
            f"{total:,} changes across {sum(1 for d in deltas if d.listed)} dimensions"
        )

    def _summary(
        self,
        deltas: list[DimensionDelta],
        settings: list[SettingDiff],
        run_diff: list[RunDifference],
    ) -> str:
        compared = sum(d.unchanged + d.changed for d in deltas)
        parts = [f"{compared:,} rows matched by identity"]
        uncovered = [
            d.label
            for d in deltas
            if d.verdict.compared and not d.verdict.covered_current
        ]
        if uncovered:
            parts.append(f"{', '.join(uncovered)} not scanned in the later run")
        material = [row for row in run_diff if row.material]
        if material:
            count = len(material)
            word = "run setting differs" if count == 1 else "run settings differ"
            parts.append(f"{count} {word}")
        if settings:
            count = len(settings)
            word = "stage setting differs" if count == 1 else "stage settings differ"
            parts.append(f"{count} {word}")
        return ". ".join(parts) + "."

    def _side_read(
        self,
        scan: Scan,
        activities: dict[UUID, dict[str, str]],
        deltas: list[DimensionDelta],
        attr: str,
    ) -> RunSide:
        ran = activities.get(scan.id, {})
        config = scan.execution_config or {}
        return RunSide(
            scan_id=scan.id,
            engine_name=scan.engine_name,
            context_name=scan.context_name,
            intensity=str(config.get("intensity") or ""),
            scope=scan.scope,
            status=scan.status,
            started_at=scan.started_at or scan.created_at,
            completed_at=scan.completed_at,
            duration_seconds=self._duration(scan),
            stages_ran=sum(1 for state in ran.values() if state in RAN),
            stages_planned=len(ran),
            counts={d.dimension: getattr(d, attr) for d in deltas},
        )

    def _comparable_read(
        self, run: Scan, activities: dict[UUID, dict[str, str]], reason: str
    ) -> ComparableRun:
        counts = self._counts(run)
        return ComparableRun(
            scan_id=run.id,
            engine_name=run.engine_name,
            status=run.status,
            scope=run.scope,
            started_at=_started_at(run),
            duration_seconds=self._duration(run),
            counts=counts,
            dimensions=[
                key
                for key in SURFACE_ORDER
                if self._ran(key, run, activities) or counts.get(key)
            ],
            comparable=reason == "",
            reason=reason,
        )

    def _counts(self, scan: Scan) -> dict[str, int]:
        return {
            SurfaceDimension.WEB_ASSETS.value: scan.subdomains_found,
            SurfaceDimension.ENDPOINTS.value: scan.endpoints_found,
            SurfaceDimension.SERVICES.value: scan.open_ports_found,
            SurfaceDimension.IPS.value: scan.ips_found,
            SurfaceDimension.VULNERABILITIES.value: scan.vulnerabilities_found,
        }

    def _duration(self, scan: Scan) -> float | None:
        start, end = scan.started_at, scan.completed_at
        if start is None or end is None:
            return None
        return (end - start).total_seconds()

    def _wanted(self, verbs: list[str], confirmed: bool) -> set[str]:
        asked = {
            v for v in verbs if v in set(LISTED_VERBS) | {ChangeVerb.UNCHANGED.value}
        }
        if not asked:
            asked = set(LISTED_VERBS)
        if confirmed:
            asked.discard(ChangeVerb.UNCONFIRMED.value)
        else:
            asked.discard(ChangeVerb.DISAPPEARED.value)
        return asked

    # ---------- row building ----------

    def _row(
        self,
        spec: DimSpec,
        row,
        columns: tuple[str, ...],
        confirmed: bool,
        baseline_id: UUID,
        current_id: UUID,
    ) -> ChangeRow:
        before = {name: row[f"a_{name}"] for name in columns}
        after = {name: row[f"b_{name}"] for name in columns}
        if row["is_appeared"]:
            verb = ChangeVerb.APPEARED.value
        elif row["is_gone"]:
            verb = (
                ChangeVerb.DISAPPEARED.value
                if confirmed
                else ChangeVerb.UNCONFIRMED.value
            )
        else:
            verb = ChangeVerb.CHANGED.value

        live = after if not row["is_gone"] else before
        fields = (
            self._fields(spec, before, after)
            if verb == ChangeVerb.CHANGED.value
            else []
        )
        if verb == ChangeVerb.CHANGED.value and not fields:
            verb = ChangeVerb.UNCHANGED.value

        return ChangeRow(
            key=self._key(spec, live),
            dimension=spec.dimension,
            verb=verb,
            signal=SIGNAL_BY_RANK.get(int(row["rank"]), ChangeSignal.ASSET_GONE.value),
            rank=int(row["rank"]),
            title=self._title(spec, live),
            subtitle=self._subtitle(spec, live),
            scan_id=baseline_id if row["is_gone"] else current_id,
            fields=fields,
            severity=live.get("severity"),
            status=live.get("http_status") or live.get("status_code"),
            port=live.get("number"),
            is_kev=bool(live.get("is_kev")),
            sensitive=bool(live.get("number") in SENSITIVE),
            screenshots=self._screenshots(before, after),
        )

    def _key(self, spec: DimSpec, values: dict) -> str:
        return "|".join(str(values.get(k) or "") for k in spec.keys)

    def _title(self, spec: DimSpec, values: dict) -> str:
        if spec.dimension == SurfaceDimension.SERVICES.value:
            return f"{values.get('ip')}:{values.get('number')}"
        return str(values.get(spec.title) or self._key(spec, values))

    def _subtitle(self, spec: DimSpec, values: dict) -> str:
        parts = [str(values.get(name)) for name in spec.subtitle if values.get(name)]
        if spec.dimension == SurfaceDimension.VULNERABILITIES.value and values.get(
            "host"
        ):
            parts.insert(0, str(values["host"]))
        return " · ".join(parts)

    def _screenshots(self, before: dict, after: dict) -> ScreenshotPair | None:
        left, right = before.get("screenshot_path"), after.get("screenshot_path")
        if not left and not right:
            return None
        return ScreenshotPair(baseline=left, current=right)

    def _fields(self, spec: DimSpec, before: dict, after: dict) -> list[ChangeField]:
        out: list[ChangeField] = []
        for field in WATCHED_FIELDS[spec.dimension]:
            if not hasattr(spec.model, field.name):
                continue
            old, new = before.get(field.name), after.get(field.name)
            if field.kind == FieldKind.OPAQUE.value:
                if _text_value(old) == _text_value(new):
                    continue
                out.append(
                    ChangeField(
                        field=field.name,
                        label=field.label,
                        before=None,
                        after="changed" if old and new else "added" if new else "gone",
                        tone=Tone.NEUTRAL.value
                        if old and new
                        else Tone.UP.value
                        if new
                        else Tone.DOWN.value,
                    )
                )
                continue
            if field.kind == FieldKind.LIST.value:
                left, right, tone = _list_delta(old, new)
                if right is None:
                    continue
                out.append(
                    ChangeField(
                        field=field.name,
                        label=field.label,
                        before=left,
                        after=right,
                        tone=tone,
                    )
                )
                continue
            if _same_value(old, new):
                continue
            tone = Tone.NEUTRAL.value
            if new in (None, "", False) and old not in (None, "", False):
                tone = Tone.DOWN.value
            elif old in (None, "", False) and new not in (None, "", False):
                tone = Tone.UP.value
            out.append(
                ChangeField(
                    field=field.name,
                    label=field.label,
                    before=_text_value(old),
                    after=_text_value(new),
                    tone=tone,
                )
            )
        return out


def compare_dimensions() -> tuple[str, ...]:
    return SURFACE_ORDER


__all__ = ["ScanCompareService", "compare_dimensions"]
