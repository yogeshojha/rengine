"""Persist AI call records from a worker process."""

from __future__ import annotations

from app.database import SyncSessionLocal
from shared.logging import get_logger
from shared.models.ai import AiCall
from shared.services.ai import ledger
from shared.services.ai.ledger import CallRecord, row_values

logger = get_logger(__name__)


def install() -> None:
    ledger.register(_write)


def _write(rec: CallRecord) -> None:
    try:
        with SyncSessionLocal() as session:
            session.add(AiCall(**row_values(rec)))
            session.commit()
    except Exception as exc:
        logger.warning("ai call not stored", task=rec.task, error=str(exc))
