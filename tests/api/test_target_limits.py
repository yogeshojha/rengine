from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.api.v1.targets import validate_target_batch
from app.services.target import TargetService
from shared.definitions.constants import MAX_TARGETS_IMPORT
from shared.models.project import Project
from shared.models.target import (
    MAX_TARGET_VALUE_LEN,
    Target,
    TargetBulkCreate,
    TargetImportItem,
    TargetImportRequest,
    TargetValidationBatch,
)

pytestmark = pytest.mark.api

LONG = "https://example.com/" + "a" * 300
TOO_LONG = "https://example.com/" + "a" * MAX_TARGET_VALUE_LEN


@pytest.fixture
def service(session, monkeypatch) -> TargetService:
    monkeypatch.setattr(session, "commit", session.flush)
    monkeypatch.setattr(
        TargetService, "_dispatch_post_target_creation", lambda *_: None
    )
    return TargetService(session)


async def _slug(session, estate) -> str:
    project = await session.scalar(
        select(Project).where(Project.id == estate.project_id)
    )
    return project.slug


async def test_a_long_value_imports_without_a_display_name(session, estate, service):
    slug = await _slug(session, estate)

    result = await service.bulk_create_targets(
        TargetBulkCreate(project_slug=slug, targets=[LONG]), str(estate.user_id)
    )

    assert result.imported == 1
    target = await session.scalar(select(Target).where(Target.target_value == LONG))
    assert target.display_name is None


async def test_an_overlong_value_fails_alone(session, estate, service):
    slug = await _slug(session, estate)

    result = await service.bulk_create_targets(
        TargetBulkCreate(project_slug=slug, targets=[TOO_LONG, "example.org"]),
        str(estate.user_id),
    )

    assert (result.imported, result.failed) == (1, 1)
    assert "longer than" in result.results[0].error


async def test_an_overlong_display_name_fails_alone(session, estate, service):
    slug = await _slug(session, estate)
    request = TargetImportRequest(
        project_slug=slug,
        targets=[
            TargetImportItem(target_value="example.net", display_name="n" * 201),
            TargetImportItem(target_value="example.org"),
        ],
    )

    result = await service.import_targets_structured(request, str(estate.user_id))

    assert (result.imported, result.failed) == (1, 1)


async def test_ensure_targets_refuses_an_overlong_value(estate, service):
    with pytest.raises(HTTPException) as exc:
        await service.ensure_targets([TOO_LONG], estate.project_id, estate.user_id)
    assert exc.value.status_code == 400


async def test_batch_validation_answers_every_value_in_order(service):
    values = [" Example.COM ", "not a target", "example.com"]

    answers = await validate_target_batch(
        TargetValidationBatch(values=values), None, service
    )

    assert [a.valid for a in answers] == [True, False, True]
    assert [a.target_value for a in answers] == [
        "example.com",
        "not a target",
        "example.com",
    ]


def test_batch_validation_is_capped_at_the_import_limit():
    with pytest.raises(ValidationError):
        TargetValidationBatch(values=["example.com"] * (MAX_TARGETS_IMPORT + 1))


async def test_batch_validation_names_the_projects_existing_target(
    session, estate, service
):
    slug = await _slug(session, estate)
    target_id = await estate.target("example.com")

    answers = await validate_target_batch(
        TargetValidationBatch(
            values=["Example.com", "new.example.org", "not a target"],
            project_slug=slug,
        ),
        None,
        service,
    )

    assert [a.target_id for a in answers] == [target_id, None, None]


async def test_batch_validation_without_a_project_matches_nothing(
    session, estate, service
):
    await estate.target("example.com")

    answers = await validate_target_batch(
        TargetValidationBatch(values=["example.com"]), None, service
    )

    assert answers[0].target_id is None


async def test_batch_validation_refuses_an_unknown_project(service):
    with pytest.raises(HTTPException):
        await validate_target_batch(
            TargetValidationBatch(values=["example.com"], project_slug="no-such"),
            None,
            service,
        )
