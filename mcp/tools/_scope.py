"""Resolve a typed name to the scans that answer for it."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import exists, func, not_
from sqlmodel import col, select

from mcp.context import ToolContext
from mcp.dimensions import Dimension
from mcp.errors import ScopeError, ToolError
from shared.definitions.surface import SURFACE_ORDER, SurfaceDimension
from shared.enums.scan import SCAN_LIVE_STATUSES
from shared.models.project import Project
from shared.models.scan import Scan
from shared.models.target import Target
from shared.models.target_summary import SurfaceMetric, TargetSummaryRead
from shared.models.vulnerability import Vulnerability
from shared.services.asset_query import vuln_suppressed


@dataclass
class Coverage:
    scan_id: uuid.UUID | None
    covered: bool
    value: int | None
    observed_at: object | None
    current: bool

    @property
    def usable(self) -> bool:
        return self.covered and self.scan_id is not None


@dataclass
class Scope:
    target: Target
    surface: dict[str, Coverage]
    summary: TargetSummaryRead | None = None

    @property
    def project_id(self) -> uuid.UUID:
        return self.target.project_id

    def metric(self, dimension: str) -> SurfaceMetric | None:
        if self.summary is None:
            return None
        return next((m for m in self.summary.surface if m.key == dimension), None)

    def coverage(self, dimension: str) -> Coverage:
        return self.surface.get(dimension) or Coverage(None, False, None, None, False)

    def require(self, dim: Dimension) -> uuid.UUID:
        found = self.coverage(dim.key)
        if not found.usable:
            msg = (
                f"{self.target.target_value}: {dim.noun_plural} not scanned. "
                "Run a scan that produces them."
            )
            raise ToolError(msg)
        return found.scan_id  # type: ignore[return-value]

    def caveat(self, dim: Dimension) -> list[str]:
        found = self.coverage(dim.key)
        notes: list[str] = []
        if found.observed_at:
            notes.append(f"Observed {found.observed_at} by scan {found.scan_id}.")
        if not found.current:
            notes.append(
                "A newer scan exists that did not cover this dimension. "
                "These figures are from the most recent covering scan."
            )
        return notes


async def resolve(
    ctx: ToolContext, value: str, *, full: bool = False, counts: bool = False
) -> Scope:
    """A target and each dimension's most recent covering scan; `full` adds the target summary."""
    match = await find_target(ctx, value)
    if full:
        from app.services.target_summary import TargetSummaryService  # noqa: PLC0415

        summary = await TargetSummaryService(ctx.session).summary(
            match.id, match.project_id
        )
        surface = {
            m.key: Coverage(m.scan_id, m.covered, m.value, m.observed_at, m.current)
            for m in summary.surface
        }
        return Scope(target=match, surface=surface, summary=summary)
    surface = await _covering(ctx, match, counts=counts)
    return Scope(target=match, surface=surface)


async def _covering(
    ctx: ToolContext, target: Target, *, counts: bool
) -> dict[str, Coverage]:
    """The target summary's covering-scan pick, counting only the picked scans."""
    from app.services import scan_deltas  # noqa: PLC0415
    from app.services.surface_scope import TABLES  # noqa: PLC0415
    from app.services.target_summary import TargetSummaryService  # noqa: PLC0415

    session = ctx.session
    service = TargetSummaryService(session)
    runs = await service._runs(target.id, target.project_id)
    if not runs:
        return {}
    ids = [r.id for r in runs]
    vuln = SurfaceDimension.VULNERABILITIES.value
    held: dict[str, dict[uuid.UUID, int]] = {vuln: {}}
    for key, model in TABLES.items():
        if key == vuln:
            continue
        found = await session.execute(
            select(Scan.id).where(
                col(Scan.id).in_(ids),
                exists(select(1).where(model.scan_id == Scan.id)),
            )
        )
        held[key] = dict.fromkeys(found.scalars(), 1)
    covered = await service._covered(runs, held)
    by_id = {r.id: r for r in runs}
    live = frozenset(r.id for r in runs if r.status in SCAN_LIVE_STATUSES)
    out: dict[str, Coverage] = {}
    for key in SURFACE_ORDER:
        if not covered[key]:
            continue
        scan = by_id[covered[key][0]]
        value = None
        if counts and key == vuln:
            value = await session.scalar(
                select(func.count())
                .select_from(Vulnerability)
                .where(
                    Vulnerability.scan_id == scan.id,
                    not_(vuln_suppressed(ids[0])),
                )
            )
        elif counts:
            rows = await scan_deltas.row_counts(
                session, key, [scan.id], live & {scan.id}
            )
            value = rows.get(scan.id, (0, None))[0]
        out[key] = Coverage(
            scan_id=scan.id,
            covered=True,
            value=int(value or 0) if counts else None,
            observed_at=scan.started_at or scan.created_at,
            current=scan.id == runs[0].id,
        )
    return out


async def find_target(ctx: ToolContext, value: str) -> Target:
    """Find one target by value, id, or unique suffix, inside the token's scope."""
    raw = (value or "").strip()
    needle = raw.lower()
    if not needle:
        msg = "Name a target: a domain, IP address, CIDR range, URL or ASN."
        raise ToolError(msg)

    scoped = ctx.scoped_projects()
    targets = ctx.scoped_targets()

    def _scoped(statement):
        statement = statement.where(col(Target.project_id).in_(active_project_ids()))
        if targets is not None:
            statement = statement.where(col(Target.id).in_(targets))
        if scoped is None:
            return statement
        return statement.where(col(Target.project_id).in_(scoped))

    direct = _scoped(
        select(Target).where(col(Target.target_value).in_({raw, needle}))
    ).limit(1)
    match = (await ctx.session.execute(direct)).scalars().first()

    if match is None and (as_id := _as_uuid(needle)) is not None:
        by_id = _scoped(select(Target).where(col(Target.id) == as_id)).limit(1)
        match = (await ctx.session.execute(by_id)).scalars().first()

    if match is None:
        match = await _loose_match(ctx, _scoped, needle)
    if match is None:
        near = (
            (
                await ctx.session.execute(
                    _scoped(select(Target.target_value))
                    .order_by(Target.target_value)
                    .limit(8)
                )
            )
            .scalars()
            .all()
        )
        if not near:
            msg = "No targets in scope."
            raise ToolError(msg)
        msg = f"No target matches {value!r}. Known targets include: {', '.join(near)}."
        raise ToolError(msg)

    ctx.check_project(match.project_id)
    ctx.check_target(match.id)
    return match


def _as_uuid(needle: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(needle)
    except ValueError:
        return None


async def _loose_match(ctx: ToolContext, scoped, needle: str) -> Target | None:
    value = func.lower(Target.target_value)
    exact = scoped(select(Target).where(value == needle)).limit(1)
    match = (await ctx.session.execute(exact)).scalars().first()
    if match is not None:
        return match
    partial = scoped(
        select(Target).where(value.contains(needle, autoescape=True))
    ).limit(2)
    rows = (await ctx.session.execute(partial)).scalars().all()
    return rows[0] if len(rows) == 1 else None


def active_projects():
    return select(Project).where(col(Project.is_active).is_(True))


def active_project_ids():
    return select(Project.id).where(col(Project.is_active).is_(True))


async def scan_in_scope(ctx: ToolContext, scan: Scan) -> None:
    """A run of a target inside the token's scope."""
    await in_scope(ctx, scan.project_id)
    ctx.check_target(scan.target_id)


async def in_scope(ctx: ToolContext, project_id: uuid.UUID) -> uuid.UUID:
    """A project inside the token's scope that has not been deleted."""
    ctx.check_project(project_id)
    row = await ctx.session.get(Project, project_id)
    if row is None or not row.is_active:
        msg = "The project does not exist."
        raise ScopeError(msg)
    return project_id


def parse_id(value: str | None, field: str) -> uuid.UUID | None:
    if not value:
        return None
    try:
        return uuid.UUID(value.strip())
    except ValueError as exc:
        msg = f"{field} must be a UUID, not {value!r}."
        raise ToolError(msg) from exc


def operator(ctx: ToolContext) -> uuid.UUID:
    """The user who issued the token, whom a change is attributed to."""
    if ctx.token.issued_by is None:
        msg = "This token has no issuing operator to attribute the change to."
        raise ToolError(msg)
    return ctx.token.issued_by


async def project_for(ctx: ToolContext, project_id: uuid.UUID | None) -> uuid.UUID:
    """Resolve the project a project-wide tool should act on."""
    if project_id is not None:
        return await in_scope(ctx, project_id)
    if ctx.token.project_id is not None:
        return ctx.token.project_id

    rows = (await ctx.session.execute(active_projects())).scalars().all()
    if len(rows) == 1:
        return rows[0].id
    if not rows:
        msg = "No projects exist."
        raise ScopeError(msg)
    names = ", ".join(f"{r.name} ({r.id})" for r in rows[:8])
    msg = f"Pass project_id. This token can see several projects: {names}."
    raise ToolError(msg)
