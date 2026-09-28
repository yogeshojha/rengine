"""Candidate domain dossier: which rows the enrichment task should refresh."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from sqlalchemy import or_, select

from shared.definitions.estate import DOSSIER_TTL_DAYS, MAX_ENRICH_PER_TICK
from shared.models.estate import EstateCandidate
from shared.utils.datetime import utc_now

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def pending(
    session: Session, limit: int = MAX_ENRICH_PER_TICK
) -> list[EstateCandidate]:
    """Candidate rows never enriched or stale past the freshness window, oldest first."""
    cutoff = utc_now() - timedelta(days=DOSSIER_TTL_DAYS)
    rows = (
        session.execute(
            select(EstateCandidate)
            .where(
                or_(
                    EstateCandidate.checked_at.is_(None),
                    EstateCandidate.checked_at < cutoff,
                )
            )
            .order_by(EstateCandidate.checked_at.asc().nulls_first())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return list(rows)
