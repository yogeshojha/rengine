from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.v1.organizations import delete_organization, update_organization
from app.api.v1.tags import delete_tag, list_tags, update_tag
from shared.definitions.surface import SurfaceDimension
from shared.definitions.tripwires import ScopeKind
from shared.enums.target import TargetType
from shared.models.organization import Organization, OrganizationUpdate
from shared.models.project import Project
from shared.models.tag import Tag, TagUpdate, TargetTag
from shared.models.target import Target
from shared.models.tripwire import Tripwire
from shared.models.user import User

pytestmark = pytest.mark.api


async def _project(durable) -> tuple[Project, User]:
    user = User(
        username=f"l{uuid.uuid4().hex[:8]}",
        email=f"{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="x",
    )
    durable.add(user)
    await durable.flush()
    project = Project(name="L", slug=f"l-{uuid.uuid4().hex[:8]}", created_by=user.id)
    durable.add(project)
    await durable.flush()
    return project, user


async def _tag(durable, project, user, name: str) -> Tag:
    tag = Tag(name=name, slug=name, project_id=project.id, created_by=user.id)
    durable.add(tag)
    await durable.flush()
    return tag


async def test_a_tag_is_renamed_recoloured_and_reslugged(durable):
    project, user = await _project(durable)
    tag = await _tag(durable, project, user, "prod typo")
    renamed = await update_tag(
        tag.id, TagUpdate(name="  Production ", color="#ef4444"), user, durable
    )
    assert (renamed.name, renamed.slug, renamed.color) == (
        "production",
        "production",
        "#EF4444",
    )


async def test_a_rename_onto_another_tag_is_refused(durable):
    project, user = await _project(durable)
    tag = await _tag(durable, project, user, "staging")
    await _tag(durable, project, user, "production")
    with pytest.raises(HTTPException) as refused:
        await update_tag(tag.id, TagUpdate(name="Production"), user, durable)
    assert refused.value.status_code == 409


async def test_an_empty_name_is_refused(durable):
    project, user = await _project(durable)
    tag = await _tag(durable, project, user, "staging")
    with pytest.raises(HTTPException) as refused:
        await update_tag(tag.id, TagUpdate(name="   "), user, durable)
    assert refused.value.status_code == 400


async def test_deleting_a_tag_keeps_its_targets(durable):
    project, user = await _project(durable)
    tag = await _tag(durable, project, user, "legacy")
    target = Target(
        target_value="example.com",
        target_type=TargetType.DOMAIN,
        project_id=project.id,
        created_by=user.id,
    )
    durable.add(target)
    await durable.flush()
    durable.add(TargetTag(target_id=target.id, tag_id=tag.id))
    await durable.commit()

    listed = await list_tags(user, durable, project_slug=project.slug)
    assert [(t.name, t.target_count) for t in listed] == [("legacy", 1)]

    await delete_tag(tag.id, user, durable)
    assert await durable.get(Target, target.id) is not None
    assert (await durable.scalars(select(TargetTag))).all() == []


async def test_a_tag_a_tripwire_is_scoped_to_is_not_deleted(durable):
    project, user = await _project(durable)
    tag = await _tag(durable, project, user, "crown jewels")
    durable.add(
        Tripwire(
            project_id=project.id,
            name="New admin panel",
            dimension=SurfaceDimension.WEB_ASSETS.value,
            scope_kind=ScopeKind.TAG.value,
            scope_ids=[str(tag.id)],
        )
    )
    await durable.commit()
    with pytest.raises(HTTPException) as refused:
        await delete_tag(tag.id, user, durable)
    assert refused.value.status_code == 409
    assert "New admin panel" in refused.value.detail


async def test_an_organization_is_renamed_and_deleted(durable):
    project, user = await _project(durable)
    org = Organization(
        name="acme corp", slug="acme-corp", project_id=project.id, created_by=user.id
    )
    durable.add(org)
    await durable.commit()
    renamed = await update_organization(
        org.id, OrganizationUpdate(name="Acme Inc", description="Parent"), user, durable
    )
    assert (renamed.name, renamed.slug, renamed.description) == (
        "acme inc",
        "acme-inc",
        "Parent",
    )
    await delete_organization(org.id, user, durable)
    assert await durable.get(Organization, org.id) is None
