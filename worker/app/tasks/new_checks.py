"""Follow-up runs with the checks the library gained."""

from __future__ import annotations

from app.database import get_sync_session
from shared.services import new_checks


def sweep() -> dict:
    with get_sync_session() as session:
        result = new_checks.sweep(session)
    return {
        "templates": result.templates,
        "targets": result.targets,
        "busy": result.busy,
        "waiting": result.waiting,
        "skipped": result.skipped,
        "failed": result.failed,
    }
