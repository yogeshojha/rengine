from __future__ import annotations

from datetime import timedelta

import pytest

from shared.definitions.datasets import DATASETS, DATASETS_BY_KIND
from shared.definitions.threat_intel import FEEDS, FeedStatus
from shared.services import locks
from shared.services.feed_ledger import dataset_status
from shared.utils.datetime import utc_now

pytestmark = pytest.mark.pipeline

NOW = utc_now()


def test_every_threat_feed_is_a_dataset():
    assert {feed.kind for feed in FEEDS} <= set(DATASETS_BY_KIND)


def test_only_the_threat_feeds_follow_the_nightly_switch():
    assert {d.kind for d in DATASETS if d.auto_sync} == {feed.kind for feed in FEEDS}


def test_every_dataset_has_its_own_lock():
    keys = [locks.dataset(d.kind) for d in DATASETS]
    assert len(set(keys)) == len(DATASETS)
    assert all(locks.DATASET_SYNC <= k <= locks.DATASET_SYNC + 0xFFFF for k in keys)


def test_dataset_locks_stay_clear_of_every_other_lock():
    ranges = [
        locks.BOUNTY_SYNC,
        locks.BOUNTY_REPORTS,
        locks.SECRET_MINING,
        locks.SOFTWARE_MATCH,
        locks.TRIPWIRE_CHECK,
    ]
    singles = [
        locks.SOFTWARE_BACKFILL,
        locks.NEW_CHECKS_SWEEP,
        locks.SCAN_ADMISSION,
        locks.SCAN_DELTAS_BACKFILL,
        locks.PROXY_DEFAULT,
    ]
    for d in DATASETS:
        key = locks.dataset(d.kind)
        assert all(not (base <= key <= base + 0xFFFF) for base in ranges)
        assert key not in singles


def test_every_dataset_names_a_loader_task():
    assert all(d.task.startswith("app.tasks.") for d in DATASETS)


def _status(**over) -> str:
    args = {
        "loading": False,
        "recorded": FeedStatus.READY.value,
        "synced_at": NOW,
        "present": True,
        "stale_after_hours": 48,
        "now": NOW,
    } | over
    return dataset_status(**args)


@pytest.mark.parametrize(
    ("over", "expected"),
    [
        ({"loading": True, "recorded": FeedStatus.FAILED.value}, FeedStatus.SYNCING),
        ({"recorded": FeedStatus.FAILED.value}, FeedStatus.FAILED),
        ({"present": False}, FeedStatus.EMPTY),
        ({"recorded": None, "synced_at": None}, FeedStatus.READY),
        ({"synced_at": NOW - timedelta(hours=49)}, FeedStatus.STALE),
        (
            {"synced_at": NOW - timedelta(hours=49), "stale_after_hours": None},
            FeedStatus.READY,
        ),
        ({"recorded": FeedStatus.SYNCING.value}, FeedStatus.READY),
        (
            {"recorded": FeedStatus.SYNCING.value, "present": False},
            FeedStatus.EMPTY,
        ),
    ],
)
def test_status_reads_the_lock_before_the_ledger(over, expected):
    assert _status(**over) == expected.value
