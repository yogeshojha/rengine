"""File findings into issue trackers, send comments, read issue status."""

from __future__ import annotations

from uuid import UUID

from celery import shared_task

from app.database import get_sync_session
from shared.services.issue_tracking import sync


@shared_task(name="app.tasks.issue_trackers.file", max_retries=0)
def file_issues(issue_ids: list[str] | None = None) -> dict:
    ids = [UUID(i) for i in issue_ids] if issue_ids else None
    with get_sync_session() as session:
        filed = sync.file_pending(session, ids)
        sync.announce(session, ids)
        sent = sync.send_comments(session, ids)
    return {"filed": filed, "comments": sent}


@shared_task(name="app.tasks.issue_trackers.refresh", max_retries=0)
def refresh() -> dict:
    with get_sync_session() as session:
        sync.sweep_pending(session)
        read = sync.refresh_statuses(session)
        sync.announce(session, None)
        sent = sync.send_comments(session, None)
    return {"read": read, "comments": sent}


@shared_task(name="app.tasks.issue_trackers.observe", max_retries=0)
def observe(scan_id: str) -> dict:
    with get_sync_session() as session:
        queued = sync.observe_scan(session, UUID(scan_id))
    return {"comments": queued}
