from __future__ import annotations

import pytest

from app.api.v1.celery_health import _queue_health
from shared.definitions.workers import QUEUES

pytestmark = pytest.mark.api


def test_every_queue_is_reported_with_its_workers():
    replies = {
        "worker-scans@a": [{"name": "scans"}],
        "worker-scans@b": [{"name": "scans"}, {"name": "scans"}],
        "worker-default@a": [{"name": "default"}, {"name": "critical"}],
    }

    health = _queue_health(replies)

    assert health.responded
    assert {q.name: q.workers for q in health.queues} == {
        "scan_control": 0,
        "scans": 2,
        "default": 1,
        "critical": 1,
    }


def test_no_reply_reports_every_queue_without_a_worker():
    health = _queue_health(None)

    assert not health.responded
    assert [q.name for q in health.queues] == [spec.name for spec in QUEUES]
    assert all(q.workers == 0 for q in health.queues)
