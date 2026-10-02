from collections.abc import Callable
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.services.asset_query import QueryScope


async def column_facet(
    session: AsyncSession,
    scope: QueryScope,
    column,
    scan_column,
    *,
    labels: dict[str, str],
    order: tuple[str, ...],
    make: Callable[..., Any],
    limit: int,
) -> list[Any]:
    """The most frequent values of one column in scope."""
    rows = await session.execute(
        select(column, func.count())
        .where(scope.match(scan_column))
        .group_by(column)
        .order_by(func.count().desc())
        .limit(limit)
    )
    found = [
        make(key=key, label=labels.get(key, key), count=count)
        for key, count in rows.all()
        if key
    ]
    if not order:
        return found
    rank = {key: index for index, key in enumerate(order)}
    return sorted(found, key=lambda item: rank.get(item.key, len(rank)))
