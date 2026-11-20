"""Project access on scans, engines, contexts, schedules, screenshots and OAST."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import update

from app.api.v1 import media as media_api
from app.services.oast import OastService
from app.services.rescan import RescanService
from app.services.scan import ScanService
from app.services.scan_engine import preview_engine
from app.services.scan_schedule import ScanScheduleService
from app.services.scan_tags import ScanTagService
from shared.definitions.evidence import Evidence
from shared.enums.scan import ScanStatus
from shared.enums.scan_schedule import ScheduleType
from shared.models.scan import RescanCreate, ScanCreate, SeedPick, SeedSelection
from shared.models.scan_context import ScanContext
from shared.models.scan_engine import EnginePreviewRequest, ScanEngine
from shared.models.scan_schedule import ScanScheduleCreate
from shared.models.vulnerability import Vulnerability
from shared.services.project_access import EVERY_PROJECT

pytestmark = pytest.mark.api


async def _refused(call) -> HTTPException:
    with pytest.raises(HTTPException) as caught:
        await call
    return caught.value


async def test_a_screenshot_of_another_project_is_not_found(
    estate, now, tmp_path, monkeypatch
):
    other = await estate.sibling()
    mine = await estate.scan("example.com", "mine", at=now)
    theirs = await other.scan("example.org", "theirs", at=now)
    for sid in (mine, theirs):
        (tmp_path / str(sid) / "screenshot").mkdir(parents=True)
        (tmp_path / str(sid) / "screenshot" / "a.png").write_bytes(b"png")
    monkeypatch.setattr(media_api, "MEDIA_ROOT", tmp_path)
    access = frozenset({estate.project_id})

    async def fetch(path: str):
        return await media_api.get_screenshot(None, access, estate.session, path)

    served = await fetch(f"{mine}/screenshot/a.png")
    assert str(served.path) == str(tmp_path / str(mine) / "screenshot" / "a.png")
    for path in (
        f"{theirs}/screenshot/a.png",
        f"{uuid.uuid4()}/screenshot/a.png",
        "a.png",
        "notascan/a.png",
    ):
        refused = await _refused(fetch(path))
        assert (refused.status_code, refused.detail) == (404, "Screenshot not found.")


async def test_the_callback_count_reads_the_callers_projects(estate, now):
    other = await estate.sibling()
    await estate.scan("example.com", "mine", at=now)
    await other.scan("example.org", "theirs", at=now)
    await estate.vulns("mine", [("own", "high")], at=now)
    await other.vulns("theirs", [("far", "high"), ("far2", "low")], at=now)
    await estate.session.execute(
        update(Vulnerability).values(evidence=Evidence.PROVEN.value)
    )
    service = OastService(estate.session)

    assert (await service.read(frozenset({estate.project_id}))).interactions == 1
    assert (await service.read(frozenset())).interactions == 0
    assert (await service.read(EVERY_PROJECT)).interactions == 3


async def test_an_engine_preview_refuses_another_projects_context(estate):
    other = await estate.sibling()
    theirs = ScanContext(
        project_id=other.project_id, created_by=estate.user_id, name="theirs"
    )
    estate.session.add(theirs)
    await estate.session.flush()
    data = EnginePreviewRequest(target_type="domain", context_id=theirs.id)

    refused = await _refused(
        preview_engine(data, estate.session, frozenset({estate.project_id}))
    )
    assert refused.status_code == 404
    assert (await preview_engine(data, estate.session, EVERY_PROJECT)).phases


async def test_trends_leave_out_another_projects_targets(estate, now):
    other = await estate.sibling()
    await estate.scan("example.com", "mine", at=now)
    await other.scan("example.org", "theirs", at=now)
    own, far = estate.targets["example.com"], other.targets["example.org"]

    trends = await ScanService(estate.session).finding_trends(
        estate.project_id, [own, far]
    )

    assert [t.target_id for t in trends] == [own]


async def test_cancel_all_refuses_another_projects_targets(estate, now):
    other = await estate.sibling()
    await estate.scan("example.com", "mine", at=now, status=ScanStatus.RUNNING.value)
    await other.scan("example.org", "theirs", at=now)
    own, far = estate.targets["example.com"], other.targets["example.org"]
    service = ScanService(estate.session)

    refused = await _refused(
        service.cancel_all(project_id=estate.project_id, target_ids=[own, far])
    )
    assert refused.status_code == 404


async def test_a_rescan_refuses_another_projects_scan(estate, now):
    other = await estate.sibling()
    await estate.scan("example.com", "mine", at=now)
    theirs = await other.scan("example.org", "theirs", at=now)
    data = RescanCreate(
        dimension="web_assets",
        selection=SeedSelection(
            dimension="web_assets",
            picks=[SeedPick(value="www.example.org", scan_id=theirs)],
        ),
    )
    service = RescanService(estate.session)

    for call in (
        service.preview(data=data, project_id=estate.project_id),
        service.create(
            data=data, project_id=estate.project_id, created_by=estate.user_id
        ),
    ):
        refused = await _refused(call)
        assert (refused.status_code, refused.detail) == (404, "Scan not found.")


async def test_a_launch_under_another_projects_run_is_refused(
    estate, flush_only, now, monkeypatch
):
    monkeypatch.setattr(ScanService, "_dispatch_scan", lambda *_: None)
    other = await estate.sibling()
    theirs = await other.scan("example.org", "theirs", at=now)
    target_id = await estate.target("example.com")
    launch = ScanCreate(target_id=target_id, parent_scan_id=theirs)

    refused = await _refused(
        ScanService(flush_only).create(launch, estate.project_id, estate.user_id)
    )
    assert (refused.status_code, refused.detail) == (404, "Scan not found.")


async def test_a_schedule_naming_another_projects_target_is_refused(estate):
    other = await estate.sibling()
    own = await estate.target("example.com")
    far = await other.target("example.org")
    engine = ScanEngine(
        project_id=estate.project_id, created_by=estate.user_id, name="e"
    )
    estate.session.add(engine)
    await estate.session.flush()
    plan = ScanScheduleCreate(
        name="nightly",
        target_ids=[own, far],
        engine_id=engine.id,
        schedule_type=ScheduleType.INTERVAL.value,
        interval_every=1,
        interval_unit="days",
    )

    service = ScanScheduleService(estate.session)

    refused = await _refused(service.create(plan, estate.project_id, estate.user_id))
    plan.target_ids = [own, uuid.uuid4()]
    unknown = await _refused(service.create(plan, estate.project_id, estate.user_id))
    assert (refused.status_code, refused.detail) == (
        unknown.status_code,
        unknown.detail,
    )


async def test_tagging_another_projects_run_is_refused(estate, now):
    other = await estate.sibling()
    mine = await estate.scan("example.com", "mine", at=now)
    theirs = await other.scan("example.org", "theirs", at=now)

    refused = await _refused(
        ScanTagService(estate.session).change(
            estate.project_id, [mine, theirs], ["x"], [], estate.user_id
        )
    )
    assert (refused.status_code, refused.detail) == (404, "Scan not found.")
