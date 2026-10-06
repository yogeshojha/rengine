from __future__ import annotations

import pytest
import sqlalchemy as sa
from sqlalchemy import func, select

from app.api.v1.activity_logs import feed_query
from app.services.target import TargetService
from shared.enums.activity import ActivityEvent
from shared.models.activity_log import ActivityLog

pytestmark = pytest.mark.api


@pytest.fixture
def service(session, monkeypatch) -> TargetService:
    monkeypatch.setattr(session, "commit", session.flush)
    return TargetService(session)


async def _count(session) -> int:
    return await session.scalar(select(func.count()).select_from(ActivityLog))


def test_no_activity_event_records_a_deletion():
    assert [e for e in ActivityEvent if e.value.endswith(".deleted")] == []


async def test_the_native_enum_holds_exactly_the_activity_events(session):
    labels = await session.scalars(
        sa.text(
            "SELECT enumlabel FROM pg_enum WHERE enumtypid = 'activityevent'::regtype"
        )
    )
    assert set(labels) == {e.name for e in ActivityEvent}


async def test_deleting_a_target_writes_no_activity(session, estate, service):
    target_id = await estate.target("gone.example")
    session.add(
        ActivityLog(
            event_type=ActivityEvent.TARGET_CREATED,
            title="Target created: gone.example",
            project_id=estate.project_id,
            target_id=target_id,
            target_value="gone.example",
        )
    )
    await session.flush()
    before = await _count(session)

    await service.delete_target(str(target_id))

    assert await _count(session) == before


async def test_the_feed_lists_run_results_and_drops_bookkeeping(session, estate):
    target_id = await estate.target("kept.example")
    for event, target, value in (
        (ActivityEvent.SCAN_COMPLETED, target_id, "kept.example"),
        (ActivityEvent.SCAN_STAGE_COMPLETED, target_id, "kept.example"),
        (ActivityEvent.TARGET_ENRICHMENT_WHOIS_FAILED, target_id, "kept.example"),
        (ActivityEvent.SCAN_FAILED, None, "deleted.example"),
        (ActivityEvent.ISSUE_FILED, None, None),
    ):
        session.add(
            ActivityLog(
                event_type=event,
                title=event.value,
                project_id=estate.project_id,
                target_id=target,
                target_value=value,
            )
        )
    await session.flush()

    rows = (await session.scalars(feed_query(estate.project_id))).all()

    assert {r.event_type for r in rows} == {
        ActivityEvent.SCAN_COMPLETED,
        ActivityEvent.ISSUE_FILED,
    }
