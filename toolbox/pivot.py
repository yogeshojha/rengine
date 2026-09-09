"""Links a result to the target reNgine already tracks for that value."""

from __future__ import annotations

from sqlmodel import select

from shared.definitions.toolbox import Pivot
from shared.models.target import Target
from toolbox.base import ToolContext


def _query(ctx: ToolContext, value: str):
    return select(Target).where(
        Target.project_id == ctx.project_id, Target.target_value == value
    )


def _pivot(row: Target | None, value: str) -> Pivot | None:
    if row is None:
        return None
    return Pivot(label=f"{value} is a target", href=f"/targets/{row.id}")


async def target_pivot(ctx: ToolContext, value: str) -> Pivot | None:
    if ctx.project_id is None or not value:
        return None
    row = (await ctx.session.execute(_query(ctx, value))).scalars().first()
    return _pivot(row, value)


def target_pivot_sync(ctx: ToolContext, value: str) -> Pivot | None:
    if ctx.project_id is None or not value:
        return None
    row = ctx.session.execute(_query(ctx, value)).scalars().first()
    return _pivot(row, value)
