"""Celery task dispatcher for sending tasks."""

from celery import Celery

from shared.config import BaseSettings_

_celery_client: Celery | None = None


def get_celery_client() -> Celery:
    global _celery_client  # noqa: PLW0603
    if _celery_client is None:
        _settings = BaseSettings_()
        _celery_client = Celery(broker=_settings.celery_broker_url)
        _celery_client.conf.update(
            task_serializer="json",
            accept_content=["json"],
        )
    return _celery_client


def dispatch_whois_lookups(target_ids: list[str]) -> None:
    """Dispatch WHOIS enrichment task for a batch of targets."""
    if not target_ids:
        return
    get_celery_client().send_task(
        "app.tasks.whois.perform_whois_lookups",
        kwargs={"target_ids": target_ids},
        queue="default",
    )
