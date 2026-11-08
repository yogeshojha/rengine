from __future__ import annotations

import pytest

from shared.sse import MAX_STREAMS_PER_OWNER, SSEManager

pytestmark = pytest.mark.api

OWNER = "sse-slots-owner"


@pytest.fixture
def manager():
    found = SSEManager()
    found._owner_streams.pop(OWNER, None)
    yield found
    found._owner_streams.pop(OWNER, None)


def test_a_claim_takes_the_slot_at_the_check(manager):
    taken = [manager.claim(OWNER) for _ in range(MAX_STREAMS_PER_OWNER + 5)]

    assert taken.count(True) == MAX_STREAMS_PER_OWNER
    assert taken[MAX_STREAMS_PER_OWNER:] == [False] * 5
    assert manager.owner_at_capacity(OWNER)


def test_a_release_frees_one_slot(manager):
    for _ in range(MAX_STREAMS_PER_OWNER):
        manager.claim(OWNER)
    manager.release(OWNER)

    assert manager.claim(OWNER)
    assert not manager.claim(OWNER)


async def test_a_claimed_stream_counts_once_and_releases_on_exit(manager):
    assert manager.claim(OWNER)
    async with manager.stream(["broadcast"], OWNER, claimed=True):
        assert manager._owner_streams[OWNER] == 1
    assert OWNER not in manager._owner_streams


async def test_an_unclaimed_stream_claims_for_itself(manager):
    async with manager.stream(["broadcast"], OWNER):
        assert manager._owner_streams[OWNER] == 1
    assert OWNER not in manager._owner_streams
