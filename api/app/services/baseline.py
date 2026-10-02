from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def new_row_ids(
    session: AsyncSession, id_column, is_new, ids: Iterable[UUID]
) -> set[UUID]:
    """The rows among ``ids`` that ``is:new`` matches."""
    wanted = list(ids)
    if not wanted:
        return set()
    found = await session.scalars(
        select(id_column).where(id_column.in_(wanted), is_new)
    )
    return set(found.all())
