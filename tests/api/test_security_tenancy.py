from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.api.v1 import targets as targets_api
from app.services.target_scope import require_target

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
