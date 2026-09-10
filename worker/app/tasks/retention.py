"""Apply the instance's retention windows, which are otherwise only a promise."""

from celery import shared_task

from app.database import get_sync_session
from shared.services.retention import enforce


@shared_task(name="app.tasks.retention.enforce")
def enforce_retention() -> dict:
    with get_sync_session() as session:
        return enforce(session).as_dict()
