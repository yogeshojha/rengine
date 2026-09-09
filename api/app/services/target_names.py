from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.target import Target


async def target_names(
    session: AsyncSession, ids: Iterable[UUID | None]
) -> dict[UUID, str]:
    wanted = {value for value in ids if value}
    if not wanted:
        return {}
    rows = await session.execute(
        select(Target.id, Target.target_value).where(Target.id.in_(wanted))
    )
    return {row[0]: row[1] for row in rows.all()}
