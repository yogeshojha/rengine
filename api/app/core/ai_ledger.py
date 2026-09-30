"""Persist AI call records from the api process."""

from __future__ import annotations

import asyncio

from app.core.database import async_db_session
from shared.logging import get_logger
from shared.models.ai import AiCall
from shared.services.ai import ledger
from shared.services.ai.ledger import CallRecord, row_values

logger = get_logger(__name__)


def install() -> None:
    loop = asyncio.get_running_loop()

    def write(rec: CallRecord) -> None:
        loop.call_soon_threadsafe(lambda: loop.create_task(_insert(rec)))

    ledger.register(write)


async def _insert(rec: CallRecord) -> None:
    try:
        async with async_db_session() as session:
            session.add(AiCall(**row_values(rec)))
            await session.commit()
    except Exception as exc:
        logger.warning("ai call not stored", task=rec.task, error=str(exc))
