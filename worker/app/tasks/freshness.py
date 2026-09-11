"""Class B: facts that need a per-asset request, refreshed on their own clock."""

from __future__ import annotations

from celery import shared_task

from app.database import get_sync_session
from shared.logging import get_logger
from shared.services import cert_freshness

logger = get_logger(__name__)


@shared_task(name="app.tasks.freshness.certificates", max_retries=0)
def certificates(limit: int = cert_freshness.MAX_PER_RUN) -> dict:
    with get_sync_session() as session:
        state = cert_freshness.refresh(session, limit=limit)
    return {
        "picked": state.picked,
        "answered": state.answered,
        "changed": state.changed,
        "renewed": state.renewed,
        "cut_short": state.cut_short,
        "skipped": state.skipped,
    }
