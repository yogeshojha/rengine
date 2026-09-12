"""Resolve a typed name to the scans that answer for it."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlmodel import select

from mcp.context import ToolContext
from mcp.dimensions import Dimension
from mcp.errors import ScopeError, ToolError
from shared.models.target import Target
from shared.models.target_summary import SurfaceMetric, TargetSummaryRead


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
    summary: TargetSummaryRead

    @property
    def project_id(self) -> uuid.UUID:
        return self.target.project_id

    def metric(self, dimension: str) -> SurfaceMetric | None:
        return next((m for m in self.summary.surface if m.key == dimension), None)

    def coverage(self, dimension: str) -> Coverage:
        metric = self.metric(dimension)
        if metric is None:
            return Coverage(None, False, None, None, False)
        return Coverage(
            scan_id=metric.scan_id,
            covered=metric.covered,
            value=metric.value,
            observed_at=metric.observed_at,
            current=metric.current,
        )

    def require(self, dim: Dimension) -> uuid.UUID:
        found = self.coverage(dim.key)
        if not found.usable:
            msg = (
                f"{dim.label} of {self.target.target_value} has not been scanned. "
                f"Report it as not scanned, not as zero. "
                f"Run a scan that produces {dim.noun_plural}."
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


async def resolve(ctx: ToolContext, value: str) -> Scope:
    """A target and what every dimension's most recent covering scan found."""
    from app.services.target_summary import TargetSummaryService  # noqa: PLC0415

    match = await find_target(ctx, value)
    summary = await TargetSummaryService(ctx.session).summary(
        match.id, match.project_id
    )
    return Scope(target=match, summary=summary)


async def find_target(ctx: ToolContext, value: str) -> Target:
    """Find one target by value, id, or unique suffix, inside the token's scope."""
    needle = (value or "").strip().lower()
    if not needle:
        msg = "Name a target: a domain, IP address, CIDR range, URL or ASN."
        raise ToolError(msg)

    statement = select(Target)
    scoped = ctx.scoped_projects()
    if scoped is not None:
        statement = statement.where(Target.project_id.in_(scoped))

    rows = (await ctx.session.execute(statement)).scalars().all()
    if not rows:
        msg = "No targets in this token's scope."
        raise ToolError(msg)

    match = _pick(rows, needle)
    if match is None:
        near = ", ".join(sorted(r.target_value for r in rows)[:8])
        msg = f"No target matches {value!r}. Known targets include: {near}."
        raise ToolError(msg)

    ctx.check_project(match.project_id)
    return match


def _pick(rows: list[Target], needle: str) -> Target | None:
    exact = [r for r in rows if r.target_value.lower() == needle]
    if exact:
        return exact[0]
    with_id = [r for r in rows if str(r.id) == needle]
    if with_id:
        return with_id[0]
    partial = [r for r in rows if needle in r.target_value.lower()]
    return partial[0] if len(partial) == 1 else None


async def project_for(ctx: ToolContext, project_id: uuid.UUID | None) -> uuid.UUID:
    """Resolve the project a project-wide tool should act on."""
    from shared.models.project import Project  # noqa: PLC0415

    if project_id is not None:
        return ctx.check_project(project_id)
    if ctx.token.project_id is not None:
        return ctx.token.project_id

    rows = (await ctx.session.execute(select(Project))).scalars().all()
    if len(rows) == 1:
        return rows[0].id
    if not rows:
        msg = "No projects exist."
        raise ScopeError(msg)
    names = ", ".join(f"{r.name} ({r.id})" for r in rows[:8])
    msg = f"Pass project_id. This token can see several projects: {names}."
    raise ToolError(msg)
