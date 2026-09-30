"""Follow-up runs with the checks the library gained."""

from __future__ import annotations

from celery import shared_task

from app.database import get_sync_session
from shared.services import new_checks


@shared_task(name="app.tasks.new_checks.sweep")
def sweep() -> dict:
    with get_sync_session() as session:
        result = new_checks.sweep(session)
    return {
        "templates": result.templates,
        "targets": result.targets,
        "busy": sum(result.busy.values()),
        "waiting": sum(result.waiting.values()),
        "skipped": sum(result.skipped.values()),
        "failed": result.failed,
    }
