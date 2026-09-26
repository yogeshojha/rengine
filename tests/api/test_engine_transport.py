"""An engine stores its own per-tool rates and concurrency."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.services.scan_engine.service import ScanEngineService
from shared.models.project import Project
from shared.models.scan_engine import ScanEngineCreate, ScanEngineUpdate
from shared.models.user import User

pytestmark = pytest.mark.api


async def _project(durable):
    uid = uuid.uuid4()
    pid = uuid.uuid4()
    durable.add(
        User(
            id=uid,
            username=f"t{uid.hex[:8]}",
            email=f"{uid.hex[:8]}@test.local",
            hashed_password="x",
            is_superuser=True,
        )
    )
    await durable.flush()
    durable.add(Project(id=pid, name="T", slug=f"t-{pid.hex[:8]}", created_by=uid))
    await durable.flush()
    return pid, uid


async def test_create_stores_and_read_returns_the_custom_rates(durable):
    pid, uid = await _project(durable)
    svc = ScanEngineService(durable)
    created = await svc.create(
        pid,
        uid,
        ScanEngineCreate(
            name="Fast", transport_overrides={"nuclei": {"rate": 40, "threads": 50}}
        ),
    )
    assert created.transport_overrides == {"nuclei": {"rate": 40, "threads": 50}}
    fetched = await svc.get(created.id, pid)
    assert fetched.transport_overrides == {"nuclei": {"rate": 40, "threads": 50}}


async def test_update_replaces_and_can_clear(durable):
    pid, uid = await _project(durable)
    svc = ScanEngineService(durable)
    created = await svc.create(
        pid,
        uid,
        ScanEngineCreate(name="Fast", transport_overrides={"httpx": {"rate": 90}}),
    )
    updated = await svc.update(
        created.id,
        pid,
        ScanEngineUpdate(transport_overrides={"nuclei": {"threads": 60}}),
    )
    assert updated.transport_overrides == {"nuclei": {"threads": 60}}
    cleared = await svc.update(
        created.id, pid, ScanEngineUpdate(transport_overrides={})
    )
    assert cleared.transport_overrides == {}


def test_the_create_schema_rejects_an_unknown_tool():
    with pytest.raises(ValidationError):
        ScanEngineCreate(name="x", transport_overrides={"nope": {"rate": 1}})
