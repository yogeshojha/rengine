from __future__ import annotations

import logging

import pytest

from app.config import settings
from app.core.database import check_capacity, pool_demand
from shared.definitions.channels import POOL_OVERFLOW, POOL_SIZE

pytestmark = pytest.mark.api


def test_demand_counts_every_pool():
    per_child = settings.WORKER_DB_POOL_SIZE + settings.WORKER_DB_MAX_OVERFLOW
    api_pool = settings.DB_POOL_SIZE + settings.DB_MAX_OVERFLOW
    api_processes = 1 if settings.API_RELOAD else settings.API_WORKERS
    expected = (
        api_processes * api_pool
        + POOL_SIZE
        + POOL_OVERFLOW
        + settings.CELERY_SCAN_CONCURRENCY * per_child
        + settings.CELERY_CONTROL_CONCURRENCY * per_child
        + settings.CELERY_DEFAULT_CONCURRENCY * per_child
        + per_child
    )
    assert pool_demand() == expected
    assert pool_demand() > settings.DB_POOL_SIZE, "a worker pool is a pool too"


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
