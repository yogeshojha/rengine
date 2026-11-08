from __future__ import annotations

import logging

import pytest

from app.config import settings
from app.core import database
from app.core.database import check_capacity, pool_demand

pytestmark = pytest.mark.api


def test_demand_counts_every_pool(monkeypatch):
    for name, value in {
        "API_RELOAD": False,
        "API_WORKERS": 2,
        "DB_POOL_SIZE": 3,
        "DB_MAX_OVERFLOW": 5,
        "WORKER_DB_POOL_SIZE": 7,
        "WORKER_DB_MAX_OVERFLOW": 11,
        "CELERY_SCAN_CONCURRENCY": 13,
        "CELERY_CONTROL_CONCURRENCY": 17,
        "CELERY_DEFAULT_CONCURRENCY": 19,
    }.items():
        monkeypatch.setattr(settings, name, value)
    monkeypatch.setattr(database, "CHANNELS_POOL_SIZE", 23)
    monkeypatch.setattr(database, "CHANNELS_POOL_OVERFLOW", 29)
    assert pool_demand() == 2 * 8 + 23 + 29 + 49 * 18 + 18


def test_demand_counts_every_api_process(monkeypatch):
    monkeypatch.setattr(settings, "API_RELOAD", False)
    monkeypatch.setattr(settings, "API_WORKERS", 4)
    single = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
    monkeypatch.setattr(settings, "API_WORKERS", 1)
    baseline = pool_demand()
    monkeypatch.setattr(settings, "API_WORKERS", 4)
    assert pool_demand() == baseline + 3 * single


async def test_the_configured_pools_fit_the_configured_server(caplog):
    with caplog.at_level(logging.WARNING):
        await check_capacity()
    assert "outgrow" not in caplog.text


async def test_it_warns_rather_than_failing_when_they_do_not(monkeypatch, caplog):
    monkeypatch.setattr(settings, "DB_MAX_OVERFLOW", 10_000)
    with caplog.at_level(logging.WARNING):
        await check_capacity()
    assert "outgrow" in caplog.text, "a silent exhaustion is a production incident"
