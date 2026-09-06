"""Drop notifications past their expiry so the inbox stays a working set."""

from celery import shared_task
from sqlalchemy import delete

from app.database import get_sync_session
from shared.logging import get_logger
from shared.models.notification import Notification
from shared.utils.datetime import utc_now

logger = get_logger(__name__)


@shared_task(name="app.tasks.notifications.cleanup")
def cleanup() -> dict:
    with get_sync_session() as session:
        result = session.execute(
            delete(Notification).where(Notification.expires_at < utc_now())
        )
        session.commit()
    removed = result.rowcount or 0
    if removed:
        logger.info("expired notifications removed", removed=removed)
    return {"removed": removed}
