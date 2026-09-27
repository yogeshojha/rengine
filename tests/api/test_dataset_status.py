from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.services.datasets import DatasetService
from shared.definitions.datasets import DATASETS, DatasetKind
from shared.definitions.threat_intel import FeedStatus
from shared.enums.instance import InstanceMode
from shared.models.instance_settings import InstanceSettings
from shared.models.threat_intel import KevEntry, ThreatFeed
from shared.services import locks

pytestmark = pytest.mark.api


async def _by_kind(session) -> dict:
    return {d.kind: d for d in await DatasetService(session).list()}


async def test_a_fresh_instance_lists_every_dataset_not_downloaded(session):
    out = await DatasetService(session).list()

    assert [d.kind for d in out] == [d.kind for d in DATASETS]
    assert {d.status for d in out} == {FeedStatus.EMPTY.value}
    assert all(d.rows is None for d in out)


async def test_corporate_mode_hides_the_program_feed(session):
    session.add(InstanceSettings(mode=InstanceMode.CORPORATE.value))
    await session.flush()

    assert DatasetKind.PROGRAM_FEED.value not in await _by_kind(session)


async def test_a_held_loader_lock_reads_as_downloading(session, engine):
    key = locks.dataset(DatasetKind.NVD.value)
    async with engine.connect() as loader:
        await loader.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        try:
            out = await _by_kind(session)
        finally:
            await loader.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    assert out[DatasetKind.NVD.value].status == FeedStatus.SYNCING.value
    assert out[DatasetKind.NVD.value].rows is None
    assert out[DatasetKind.KEV.value].status == FeedStatus.EMPTY.value


async def test_a_table_under_load_is_not_waited_on(session, engine):
    async with engine.connect() as loader:
        await loader.execute(text("BEGIN"))
        await loader.execute(text("LOCK TABLE kev_entries IN ACCESS EXCLUSIVE MODE"))
        try:
            out = await _by_kind(session)
        finally:
            await loader.execute(text("ROLLBACK"))

    assert out[DatasetKind.KEV.value].status == FeedStatus.SYNCING.value
    assert out[DatasetKind.EPSS.value].status == FeedStatus.EMPTY.value


async def test_a_failed_load_reports_its_error(session):
    session.add(
        ThreatFeed(
            kind=DatasetKind.KEV.value,
            status=FeedStatus.FAILED.value,
            error="kev.data returned 503",
        )
    )
    await session.flush()

    kev = (await _by_kind(session))[DatasetKind.KEV.value]

    assert kev.status == FeedStatus.FAILED.value
    assert kev.error == "kev.data returned 503"


async def test_rows_are_counted_in_the_table_the_noun_names(session):
    session.add(KevEntry(cve="CVE-2024-0001"))
    session.add(
        ThreatFeed(kind=DatasetKind.KEV.value, status=FeedStatus.READY.value, rows=999)
    )
    await session.flush()

    kev = (await _by_kind(session))[DatasetKind.KEV.value]

    assert kev.status == FeedStatus.READY.value
    assert kev.rows == 1


async def test_an_unknown_dataset_is_not_found(session):
    with pytest.raises(HTTPException) as refused:
        await DatasetService(session).sync("bogus")
    assert refused.value.status_code == 404


async def test_a_dataset_the_mode_hides_is_not_found(session):
    session.add(InstanceSettings(mode=InstanceMode.CORPORATE.value))
    await session.flush()

    with pytest.raises(HTTPException) as refused:
        await DatasetService(session).sync(DatasetKind.PROGRAM_FEED.value)
    assert refused.value.status_code == 404
