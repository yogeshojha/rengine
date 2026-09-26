from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.services.organization import OrganizationService
from app.services.project import ProjectService, require_project_id
from app.services.tag import TagService
from app.services.whois_record import WhoisRecordService
from shared.models.organization import OrganizationCreate, OrganizationUpdate
from shared.models.project import Project
from shared.models.tag import PREDEFINED_TAGS, TagCreate, TagUpdate

pytestmark = pytest.mark.api

NOT_FOUND = 404
CONFLICT = 409


def _slug(estate) -> str:
    return f"test-{estate.project_id.hex[:8]}"


async def test_a_slug_naming_no_project_is_a_404(estate):
    with pytest.raises(HTTPException) as caught:
        await require_project_id(estate.session, "no-such-project")
    assert caught.value.status_code == NOT_FOUND
    assert await require_project_id(estate.session, _slug(estate)) == estate.project_id


async def test_a_tag_is_created_read_renamed_and_deleted_through_its_project(estate):
    service = TagService(estate.session)
    tag = await service.create(
        TagCreate(name="Lead", color="#112233", project_slug=_slug(estate)),
        estate.user_id,
    )
    assert tag.name == "lead"
    assert (await service.get(_slug(estate), tag.slug)).id == tag.id
    assert [t.id for t in await service.list(_slug(estate))] == [tag.id]
    assert await service.list("no-such-project") == []

    renamed = await service.update(_slug(estate), tag.slug, TagUpdate(name="Hot"))
    assert renamed.slug == "hot"

    await service.delete(_slug(estate), "hot")
    with pytest.raises(HTTPException) as caught:
        await service.get(_slug(estate), "hot")
    assert caught.value.status_code == NOT_FOUND


async def test_a_second_tag_of_the_same_name_is_a_conflict(estate):
    service = TagService(estate.session)
    data = TagCreate(name="dup", color="#112233", project_slug=_slug(estate))
    await service.create(data, estate.user_id)
    with pytest.raises(HTTPException) as caught:
        await service.create(data, estate.user_id)
    assert caught.value.status_code == CONFLICT


async def test_a_tag_for_an_unknown_project_is_a_404(estate):
    with pytest.raises(HTTPException) as caught:
        await TagService(estate.session).create(
            TagCreate(name="x", color="#112233", project_slug="no-such-project"),
            estate.user_id,
        )
    assert caught.value.status_code == NOT_FOUND


async def test_predefined_tags_are_added_once(estate):
    service = TagService(estate.session)
    first = await service.init_predefined(_slug(estate), estate.user_id)
    again = await service.init_predefined(_slug(estate), estate.user_id)
    assert len(first) == len(PREDEFINED_TAGS)
    assert again == []


async def test_renaming_an_organization_onto_another_is_a_conflict(estate):
    service = OrganizationService(estate.session)
    await service.create(
        OrganizationCreate(name="Acme", project_slug=_slug(estate)), estate.user_id
    )
    other = await service.create(
        OrganizationCreate(name="Globex", project_slug=_slug(estate)), estate.user_id
    )
    with pytest.raises(HTTPException) as caught:
        await service.update(
            _slug(estate), other.slug, OrganizationUpdate(name="ACME ")
        )
    assert caught.value.status_code == CONFLICT

    same = await service.update(
        _slug(estate), other.slug, OrganizationUpdate(name=" Globex")
    )
    assert same.name == "globex"


async def test_a_project_summary_counts_its_rows_and_a_deleted_project_is_gone(
    estate,
):
    await estate.target("example.com")
    await TagService(estate.session).create(
        TagCreate(name="one", color="#112233", project_slug=_slug(estate)),
        estate.user_id,
    )
    service = ProjectService(estate.session)
    summary = await service.summary(_slug(estate))
    assert summary.stats == {"targets": 1, "organizations": 0, "tags": 1}

    await service.deactivate(_slug(estate))
    with pytest.raises(HTTPException) as caught:
        await service.get(_slug(estate))
    assert caught.value.status_code == NOT_FOUND
    project = await estate.session.scalar(
        select(Project).where(Project.id == estate.project_id)
    )
    assert project is not None
    assert project.is_active is False


async def test_a_target_without_a_whois_record_has_none(estate):
    target_id = await estate.target("example.com")
    service = WhoisRecordService(estate.session)
    assert await service.for_target(str(target_id)) is None
    assert await service.correlations_for_target(target_id) == []
    assert await service.correlations_for_target(uuid.uuid4()) == []
    with pytest.raises(HTTPException) as caught:
        await service.get(str(uuid.uuid4()))
    assert caught.value.status_code == NOT_FOUND
