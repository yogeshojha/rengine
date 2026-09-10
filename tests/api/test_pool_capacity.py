"""Every pool together must fit inside the server, and say so when it does not."""

from __future__ import annotations

import logging

import pytest

from app.config import settings
from app.core.database import check_capacity, pool_demand

pytestmark = pytest.mark.api


def test_demand_counts_every_pool():
    per_child = settings.WORKER_DB_POOL_SIZE + settings.WORKER_DB_MAX_OVERFLOW
    expected = (
        settings.DB_POOL_SIZE
        + settings.DB_MAX_OVERFLOW
        + settings.CELERY_SCAN_CONCURRENCY * per_child
        + per_child
    )
    assert pool_demand() == expected
    assert pool_demand() > settings.DB_POOL_SIZE, "a worker pool is a pool too"


async def test_the_configured_pools_fit_the_configured_server(caplog):
    """The shipped defaults must not be able to exhaust the shipped server."""
    with caplog.at_level(logging.WARNING):
        await check_capacity()
    assert "outgrow" not in caplog.text


async def test_it_warns_rather_than_failing_when_they_do_not(monkeypatch, caplog):
    monkeypatch.setattr(settings, "DB_MAX_OVERFLOW", 10_000)
    with caplog.at_level(logging.WARNING):
        await check_capacity()
    assert "outgrow" in caplog.text, "a silent exhaustion is a production incident"
