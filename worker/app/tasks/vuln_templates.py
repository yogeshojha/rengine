"""Refresh and re-index the vulnerability check library."""

from celery import shared_task

from app.database import get_sync_session
from shared.logging import get_logger
from shared.services.vuln_templates import (
    TemplateOrigin,
    custom_root,
    index_directory,
    sync_official,
)

logger = get_logger(__name__)


@shared_task(name="app.tasks.vuln_templates.sync")
def sync() -> dict:
    with get_sync_session() as session:
        official = sync_official(session)
        custom = 0
        root = custom_root()
        if root.exists():
            custom = index_directory(session, root, TemplateOrigin.CUSTOM.value)
    logger.info("check library synced", official=official, custom=custom)
    return {"official": official, "custom": custom}
