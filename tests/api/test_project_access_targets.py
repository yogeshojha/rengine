"""Targets, organizations, cloud storage and lookalikes refuse rows of a project outside the access."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from app.api.v1 import cloud_storage, lookalikes, organizations
from app.api.v1 import targets as targets_api
from app.services.cloud_storage import CloudStorageService
from app.services.lookalikes import LookalikeService
from app.services.target import TargetService
from shared.enums.target import EnrichmentKind
from shared.models import (
    Target,
    TargetBulkCreate,
    TargetCreate,
    TargetImportItem,
    TargetImportRequest,
    TargetSeedWrite,
    TargetUpdate,
)
from shared.models.organization import OrganizationCreate, OrganizationUpdate
from shared.models.tag import Tag
from shared.services.organization import get_or_create_organization
from shared.services.project_access import EVERY_PROJECT

pytestmark = pytest.mark.api


async def _refused(call) -> tuple[int, str]:
    with pytest.raises(HTTPException) as caught:
        await call
    return caught.value.status_code, caught.value.detail


@pytest.fixture
def service(flush_only, monkeypatch) -> TargetService:
    monkeypatch.setattr(
        TargetService, "_dispatch_post_target_creation", lambda *_: None
    )
    return TargetService(flush_only)


@pytest.fixture
async def world(estate):
    other = await estate.sibling(name="Theirs")
    own = await estate.target("own.example")
    theirs = await other.target("theirs.example")
    return estate, other, own, theirs, frozenset({estate.project_id})


def _by_id(service: TargetService, target_id: str, mine):
    s = service
    return [
        s.get_target(target_id, access=mine),
        s.get_target_detail(target_id, access=mine),
        s.get_target_dns(target_id, access=mine),
        s.get_target_bgp(target_id, access=mine),
        s.list_seeds(target_id, access=mine),
        s.write_seeds(target_id, TargetSeedWrite(values=["a.x"]), access=mine),
        s.delete_seed(target_id, uuid.uuid4(), access=mine),
        s.update_target(target_id, TargetUpdate(display_name="x"), "u", access=mine),
        s.refresh_target_dns(target_id, access=mine),
        s.refresh_target_whois(target_id, access=mine),
        s.refresh_target_infostealer(target_id, access=mine),
        s.refresh_target_bgp(target_id, access=mine),
        s.delete_target(target_id, access=mine),
    ]


async def test_every_target_read_and_write_refuses_another_project(world, service):
    estate, _, own, theirs, mine = world

    assert (await service.get_target(str(own), access=mine)).id == own
    for row_id in (theirs, uuid.uuid4()):
        for call in _by_id(service, str(row_id), mine):
            assert await _refused(call) == (404, "Target not found.")
    kept = await estate.session.get(Target, theirs)
    assert kept is not None
    assert kept.display_name is None


async def test_an_administrator_reads_every_project_target(world, service):
    _, _, _, theirs, _ = world
    read = await service.get_target(str(theirs), access=EVERY_PROJECT)
    assert read.id == theirs


async def test_a_bulk_write_naming_another_project_is_refused_whole(world, service):
    estate, _, own, theirs, mine = world
    ids = [own, theirs]

    for call in (
        service.bulk_add_tags(ids, ["t"], str(estate.user_id), access=mine),
        service.bulk_add_organizations(ids, ["o"], str(estate.user_id), access=mine),
        service.bulk_enrich(ids, EnrichmentKind.WHOIS, access=mine),
        service.bulk_add_tags([own, uuid.uuid4()], ["t"], "u", access=mine),
    ):
        assert await _refused(call) == (404, "Target not found.")
    tags = await estate.session.scalar(select(func.count()).select_from(Tag))
    assert tags == 0

    assert await service.bulk_add_tags([own], ["t"], str(estate.user_id), access=mine)
    tags = await estate.session.scalar(select(func.count()).select_from(Tag))
    assert tags == 1


async def test_a_target_is_never_created_in_another_project(world, service):
    estate, other, _, _, mine = world
    user = str(estate.user_id)
    calls = [
        service.create_target(
            TargetCreate(target_value="new.example", project_slug=other.slug),
            user,
            access=mine,
        ),
        service.bulk_create_targets(
            TargetBulkCreate(project_slug=other.slug, targets=["new.example"]),
            user,
            access=mine,
        ),
        service.import_targets_structured(
            TargetImportRequest(
                project_slug=other.slug,
                targets=[TargetImportItem(target_value="new.example")],
            ),
            user,
            access=mine,
        ),
        service.existing_targets(other.slug, ["theirs.example"], access=mine),
    ]
    for call in calls:
        assert await _refused(call) == (404, "Project not found.")
    created = await estate.session.scalar(
        select(func.count()).where(Target.target_value == "new.example")
    )
    assert created == 0


async def test_lists_and_search_read_the_callers_projects(world, service):
    estate, _, own, theirs, mine = world

    listed = await estate.session.scalars(await service.list_targets(projects=mine))
    found = await estate.session.scalars(
        await service.search_targets_by_value("example", mine)
    )
    every = await estate.session.scalars(
        await service.search_targets_by_value("example", EVERY_PROJECT)
    )

    assert [t.id for t in listed.all()] == [own]
    assert [t.id for t in found.all()] == [own]
    assert {t.id for t in every.all()} == {own, theirs}


async def test_an_infostealer_report_of_another_project_is_not_found(world):
    estate, _, _, theirs, mine = world
    for row_id in (theirs, uuid.uuid4()):
        refused = await _refused(
            targets_api.get_target_infostealer(
                target_id=row_id,
                _current_user=None,
                session=estate.session,
                access=mine,
            )
        )
        assert refused == (404, "Target not found.")


async def test_an_organization_of_another_project_is_not_found(world, flush_only):
    estate, other, _, _, mine = world
    org = await get_or_create_organization(
        "theirs", other.project_id, estate.user_id, flush_only
    )
    s = flush_only

    for row_id in (org.id, uuid.uuid4()):
        for call in (
            organizations.update_organization(
                organization_id=row_id,
                organization_in=OrganizationUpdate(name="renamed"),
                _current_user=None,
                access=mine,
                session=s,
            ),
            organizations.delete_organization(
                organization_id=row_id, _current_user=None, access=mine, session=s
            ),
        ):
            assert await _refused(call) == (404, "Organization not found.")
    created = organizations.create_organization(
        organization_in=OrganizationCreate(name="new", project_slug=other.slug),
        current_user=None,
        access=mine,
        session=s,
    )
    assert await _refused(created) == (404, "Project not found.")
    await s.refresh(org)
    assert org.name == "theirs"


async def test_a_scan_of_another_project_is_not_found(world, now):
    estate, other, _, _, _ = world
    theirs = await other.scan("theirs.example", "theirs", at=now)
    s = estate.session

    for call in (
        cloud_storage.scan_cloud_storage(
            _current_user=None,
            service=CloudStorageService(s),
            project_id=estate.project_id,
            scan_id=theirs,
        ),
        lookalikes.scan_lookalikes(
            _current_user=None,
            service=LookalikeService(s),
            project_id=estate.project_id,
            scan_id=theirs,
        ),
    ):
        assert await _refused(call) == (404, "Scan not found.")
