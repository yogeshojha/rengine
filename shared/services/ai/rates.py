"""A saved provider's stored rates, kept at today's price."""

from __future__ import annotations

from sqlalchemy import select

from shared.definitions.ai import MODEL_LIST_TIMEOUT, Rates
from shared.logging import get_logger
from shared.models.ai import AiConnection
from shared.services.ai import prices
from shared.services.ai.client import current_rates
from shared.services.ai.config import connection_config
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


def stored(row: AiConnection) -> Rates | None:
    if row.input_per_mtok is None or row.output_per_mtok is None:
        return None
    return Rates(
        row.input_per_mtok,
        row.output_per_mtok,
        row.cache_read_per_mtok,
        row.cache_write_per_mtok,
    )


def store(row: AiConnection, rates: Rates | None) -> None:
    row.input_per_mtok = rates.input if rates else None
    row.output_per_mtok = rates.output if rates else None
    row.cache_read_per_mtok = rates.cache_read if rates else None
    row.cache_write_per_mtok = rates.cache_write if rates else None


def apply(row: AiConnection, rates: Rates | None) -> bool:
    """Store a found price over the stored one."""
    if rates is None or rates == stored(row):
        return False
    store(row, rates)
    row.updated_at = utc_now()
    return True


def lookup(row: AiConnection) -> Rates | None:
    """What a saved provider's model costs today."""
    if not row.model:
        return None
    return current_rates(connection_config(row, timeout=MODEL_LIST_TIMEOUT))


def refresh_all(session) -> dict:
    """The price list, then every saved provider at today's price."""
    try:
        models = prices.load(session)
    except Exception:
        logger.warning("ai price list not loaded", exc_info=True)
        models = None
    rows = list(session.execute(select(AiConnection)).scalars())
    repriced = 0
    for row in rows:
        try:
            repriced += apply(row, lookup(row))
        except Exception:
            logger.warning("ai price not refreshed", connection=row.name, exc_info=True)
    session.commit()
    return {"models": models, "connections": len(rows), "repriced": repriced}
