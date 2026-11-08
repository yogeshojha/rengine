from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.api.v1 import cloud_storage, domain_posture, lookalikes
from app.api.v1 import targets as targets_api
from app.services.cloud_storage import CloudStorageService
from app.services.domain_posture import DomainPostureService
from app.services.lookalikes import LookalikeService
from app.services.scan_engine import ScanEngineService
from app.services.target_assets import TargetAssetService
from app.services.target_scope import require_target
from app.services.target_summary import TargetSummaryService
from shared.models.target_asset import TargetAssetFilter

pytestmark = pytest.mark.api


async def _refused(call) -> str:
    with pytest.raises(HTTPException) as caught:
        await call
    assert caught.value.status_code == 404
    return caught.value.detail


async def test_a_target_of_another_project_is_not_found(estate):
    tid = await estate.target("example.com")
    await require_target(estate.session, estate.project_id, tid)
    detail = await _refused(require_target(estate.session, uuid.uuid4(), tid))
    assert detail == "Target not found."


async def test_the_estate_refuses_a_scan_of_another_target(estate, now):
    own = await estate.target("example.com")
    await estate.scan("example.com", "own", at=now)
    other = await estate.scan("example.org", "other", at=now)
    detail = await _refused(
        targets_api.get_target_estate(
            target_id=own,
            _current_user=None,
            session=estate.session,
            project_id=estate.project_id,
            scan_id=other,
        )
    )
    assert detail == "Scan not found."
    await require_target(estate.session, estate.project_id, own, estate.scans["own"])


async def test_target_reads_refuse_a_target_of_another_project(estate):
    tid = await estate.target("example.com")
    other = uuid.uuid4()
    s = estate.session
    calls = [
        targets_api.get_target_summary(
            target_id=tid,
            _current_user=None,
            service=TargetSummaryService(s),
            project_id=other,
        ),
        targets_api.search_target_assets(
            target_id=tid,
            body=TargetAssetFilter(),
            _current_user=None,
            service=TargetAssetService(s),
            project_id=other,
        ),
        targets_api.get_target_relations(
            target_id=tid, _current_user=None, session=s, project_id=other
        ),
        targets_api.get_target_programs(
            target_id=tid, _current_user=None, session=s, project_id=other
        ),
        domain_posture.target_domain_posture(
            _current_user=None,
            service=DomainPostureService(s),
            target_id=tid,
            project_id=other,
        ),
        cloud_storage.target_cloud_storage(
            _current_user=None,
            service=CloudStorageService(s),
            target_id=tid,
            project_id=other,
        ),
        lookalikes.target_lookalikes(
            _current_user=None,
            service=LookalikeService(s),
            target_id=tid,
            project_id=other,
        ),
    ]
    for call in calls:
        assert await _refused(call) == "Target not found."


@pytest.mark.parametrize(
    ("document", "detail"),
    [
        ("name: [1, 2]\nstages: 3\n", "Engine YAML does not describe an engine."),
        ("name: x\n  bad: : :\n", "Engine YAML is not valid at line 2, column 6."),
        ("- a\n", "Engine YAML must be a mapping."),
        ("name: x\nintensity: [1]\n", "Engine field intensity is not valid."),
    ],
)
async def test_an_engine_import_error_names_the_problem_alone(estate, document, detail):
    with pytest.raises(HTTPException) as caught:
        await ScanEngineService(estate.session).import_yaml(
            estate.project_id, estate.user_id, document
        )
    assert caught.value.status_code == 400
    assert caught.value.detail == detail
