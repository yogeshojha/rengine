"""One page of a scope and its match count, read in a single execution."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select

from shared.definitions.asset_query import COUNT_CAP

if TYPE_CHECKING:
    from sqlalchemy import Select
    from sqlalchemy.ext.asyncio import AsyncSession

MATCHED_TOTAL = func.count().over().label("matched_total")


async def page_rows(
    session: AsyncSession,
    base: Select,
    order: Callable[[Select], Select],
    *,
    limit: int,
    offset: int,
    capped: bool = False,
) -> tuple[Sequence[Any], int]:
    """The page's rows and how many rows matched, counted to the cap when `capped`."""
    if offset >= COUNT_CAP:
        reached = await session.scalar(
            select(func.count()).select_from(
                base.order_by(None).limit(offset + 1).subquery()
            )
        )
        if int(reached or 0) <= offset:
            return [], min(int(reached or 0), COUNT_CAP + 1)
    total = MATCHED_TOTAL
    if capped:
        total = (
            select(func.count())
            .select_from(base.order_by(None).limit(COUNT_CAP + 1).subquery())
            .scalar_subquery()
            .label(MATCHED_TOTAL.name)
        )
    rows = (
        (
            await session.execute(
                order(base.add_columns(total)).limit(limit).offset(offset)
            )
        )
        .mappings()
        .all()
    )
    if rows:
        return rows, int(rows[0][MATCHED_TOTAL.name])
    if not offset:
        return rows, 0
    counted = await session.scalar(
        select(func.count()).select_from(base.limit(COUNT_CAP + 1).subquery())
    )
    return rows, int(counted or 0)
